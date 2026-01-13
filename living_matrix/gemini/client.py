"""
Gemini API Client for Image Generation.

This module provides a client for Google Gemini's image generation
capabilities using the official google-genai Python library.

Features:
- Reads GEMINI_API_KEY from environment
- 4K resolution image generation
- Timeout-safe requests
- Retry once on failure
- Never blocks simulation loop (caller responsible for async)
- Graceful failure handling

Note: This client is OBSERVATIONAL ONLY. It consumes state snapshots
and generates images but never modifies simulation data.
"""

import os
import logging
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from io import BytesIO

logger = logging.getLogger(__name__)

# Try to import the official Gemini library
try:
    from google import genai
    from google.genai import types
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False
    genai = None
    types = None


class GeminiError(Exception):
    """Exception for Gemini API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


@dataclass
class ImageResult:
    """Result from image generation."""
    image_data: bytes  # Raw image bytes (PNG/JPEG)
    mime_type: str  # "image/png" or "image/jpeg"
    generation_time_ms: int  # Time taken to generate
    prompt_used: str  # The prompt that was used


class GeminiClient:
    """
    Client for Google Gemini API image generation using official library.
    
    Uses the google-genai library to generate Matrix-style images from prompts.
    The client is stateless and thread-safe.
    
    Environment Variables:
        GEMINI_API_KEY: Required. Your Google Gemini API key.
        GEMINI_ENABLED: Optional. Set to "false" to disable (default: true).
        GEMINI_TIMEOUT: Optional. Request timeout in seconds (default: 180).
        GEMINI_RESOLUTION: Optional. Image resolution "1K", "2K", "4K" (default: "4K").
        GEMINI_ASPECT_RATIO: Optional. Aspect ratio (default: "16:9").
    """
    
    # Model for image generation (gemini-3-pro-image-preview for 4K support)
    IMAGE_MODEL = "gemini-3-pro-image-preview"
    
    # Valid aspect ratios
    VALID_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
    
    # Valid resolutions
    VALID_RESOLUTIONS = ["1K", "2K", "4K"]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 180,
        max_retries: int = 1,
        resolution: str = "4K",
        aspect_ratio: str = "16:9"
    ):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            timeout: Request timeout in seconds (default 180 for 4K)
            max_retries: Number of retries on failure (default 1)
            resolution: Image resolution "1K", "2K", or "4K" (default "4K")
            aspect_ratio: Aspect ratio (default "16:9")
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.timeout = int(os.getenv("GEMINI_TIMEOUT", str(timeout)))
        self.max_retries = max_retries
        self._enabled = os.getenv("GEMINI_ENABLED", "true").lower() not in ("false", "0", "no", "off")
        
        # Image settings
        self.resolution = os.getenv("GEMINI_RESOLUTION", resolution)
        if self.resolution not in self.VALID_RESOLUTIONS:
            logger.warning(f"Invalid resolution {self.resolution}, using 4K")
            self.resolution = "4K"
        
        self.aspect_ratio = os.getenv("GEMINI_ASPECT_RATIO", aspect_ratio)
        if self.aspect_ratio not in self.VALID_ASPECT_RATIOS:
            logger.warning(f"Invalid aspect ratio {self.aspect_ratio}, using 16:9")
            self.aspect_ratio = "16:9"
        
        # Initialize the client
        self._client = None
        if _HAS_GENAI and self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized (model: {self.IMAGE_MODEL}, resolution: {self.resolution}, aspect: {self.aspect_ratio})")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self._client = None
        elif not _HAS_GENAI:
            logger.warning("google-genai library not installed. Run: pip install google-genai")
    
    @property
    def is_available(self) -> bool:
        """Check if Gemini client is available and configured."""
        return bool(self._client) and self._enabled
    
    def generate_image(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        resolution: Optional[str] = None
    ) -> Optional[ImageResult]:
        """
        Generate a 4K image using Gemini API.
        
        Args:
            prompt: The image generation prompt
            system_prompt: Optional system instruction (prepended to prompt)
            aspect_ratio: Override aspect ratio (default uses client setting)
            resolution: Override resolution (default uses client setting)
        
        Returns:
            ImageResult with image data, or None on failure
        
        Raises:
            GeminiError: On API errors (after retries exhausted)
        """
        if not self.is_available:
            logger.debug("Gemini client not available (no API key or disabled)")
            return None
        
        start_time = time.time()
        last_error = None
        
        # Use overrides or defaults
        use_aspect_ratio = aspect_ratio or self.aspect_ratio
        use_resolution = resolution or self.resolution
        
        # Combine system prompt with user prompt if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        for attempt in range(self.max_retries + 1):
            try:
                result = self._do_generate(full_prompt, use_aspect_ratio, use_resolution)
                if result:
                    generation_time = int((time.time() - start_time) * 1000)
                    return ImageResult(
                        image_data=result[0],
                        mime_type=result[1],
                        generation_time_ms=generation_time,
                        prompt_used=prompt
                    )
            except GeminiError as e:
                last_error = e
                # Don't retry on rate limits - let the worker handle backoff
                if e.status_code == 429:
                    raise
                if not e.retryable or attempt >= self.max_retries:
                    raise
                logger.warning(f"Gemini request failed (attempt {attempt + 1}), retrying: {e}")
                time.sleep(2)  # Brief delay before retry
            except Exception as e:
                logger.error(f"Unexpected error in Gemini request: {e}")
                last_error = GeminiError(str(e), retryable=False)
                if attempt >= self.max_retries:
                    raise last_error
        
        return None
    
    def _do_generate(self, prompt: str, aspect_ratio: str, resolution: str) -> Optional[Tuple[bytes, str]]:
        """
        Execute the actual API request using official library.
        
        Args:
            prompt: The full prompt to generate
            aspect_ratio: Image aspect ratio
            resolution: Image resolution (1K, 2K, 4K)
        
        Returns:
            Tuple of (image_bytes, mime_type) or None
        """
        try:
            # Generate content with image config for 4K
            response = self._client.models.generate_content(
                model=self.IMAGE_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=resolution
                    ),
                )
            )
            
            # Extract image from response parts (official pattern)
            if response and response.parts:
                for part in response.parts:
                    # Skip text parts
                    if part.text is not None:
                        continue
                    
                    # Check for image using as_image() method
                    try:
                        image = part.as_image()
                        if image:
                            # Convert PIL Image to bytes
                            buffer = BytesIO()
                            image.save(buffer, format='PNG')
                            image_data = buffer.getvalue()
                            return (image_data, "image/png")
                    except Exception:
                        pass
                    
                    # Fallback: check inline_data directly
                    if hasattr(part, 'inline_data') and part.inline_data is not None:
                        mime_type = getattr(part.inline_data, 'mime_type', None) or "image/png"
                        image_data = getattr(part.inline_data, 'data', None)
                        if image_data:
                            if isinstance(image_data, str):
                                import base64
                                image_data = base64.b64decode(image_data)
                            return (image_data, mime_type)
            
            # Fallback: check candidates structure
            if response and hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                mime_type = part.inline_data.mime_type or "image/png"
                                image_data = part.inline_data.data
                                if image_data:
                                    if isinstance(image_data, str):
                                        import base64
                                        image_data = base64.b64decode(image_data)
                                    return (image_data, mime_type)
            
            logger.warning("No image data in Gemini response")
            return None
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"Gemini error: {e}")
            
            # Check for rate limit errors
            if "429" in str(e) or "rate" in error_str or "quota" in error_str:
                raise GeminiError("Rate limit exceeded", status_code=429, retryable=True)
            
            # Check for server errors (retryable)
            if "500" in str(e) or "503" in str(e) or "unavailable" in error_str:
                raise GeminiError(f"Server error: {e}", status_code=503, retryable=True)
            
            # Check for auth errors
            if "401" in str(e) or "403" in str(e) or "auth" in error_str:
                raise GeminiError(f"Authentication error: {e}", status_code=401, retryable=False)
            
            # Other errors
            raise GeminiError(f"API error: {e}", retryable=False)
    
    def test_connection(self) -> bool:
        """
        Test if Gemini API is reachable and key is valid.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.is_available:
            return False
        
        try:
            # Simple test - list models
            models = self._client.models.list()
            return models is not None
        except Exception as e:
            logger.debug(f"Gemini connection test failed: {e}")
            return False


# Singleton client instance
_client: Optional[GeminiClient] = None


def get_client() -> GeminiClient:
    """Get the singleton Gemini client instance."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
