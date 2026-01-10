# Contributing to Living Matrix

Thank you for your interest in contributing to Living Matrix! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain the project's vision of a living, autonomous simulation system

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant error messages or logs

### Suggesting Features

Feature suggestions are welcome! Please include:

- Clear description of the feature
- Use case or motivation
- Potential implementation approach (if you have ideas)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed
4. **Test your changes**
   - Run existing tests: `python -m pytest tests/`
   - Test manually if applicable
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
   - Use clear, descriptive commit messages
6. **Push to your branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and reasonably sized

### Architecture Principles

- **No LLM Dependencies**: Keep the system deterministic + stochastic
- **Autonomous Execution**: World must continue even if no user connects
- **Goal-Driven Behavior**: Agents act based on internal goals, not scripts
- **Living System Feel**: Things happen because of internal goals, pressure, memory, and consequences
- **Backward Compatibility**: Don't break existing functionality without good reason

### Testing

- Add tests for new features when possible
- Ensure existing tests still pass
- Test edge cases and error conditions

### Documentation

- Update README.md if adding major features
- Add docstrings to new functions/classes
- Update API documentation if changing endpoints
- Keep examples up to date

## Project Structure

Key areas to understand:

- `living_matrix/core.py` - Main simulation loop
- `living_matrix/api/` - FastAPI backend
- `living_matrix/world_sim/` - World simulation systems
- `living_matrix/intent.py`, `tension.py`, `causality.py` - Advanced AI systems
- `living_matrix/memory.py` - Memory systems (episodic, semantic, emotional, rules)

## Areas for Contribution

### High Priority

- Performance optimizations
- Bug fixes
- Test coverage improvements
- Documentation improvements

### Medium Priority

- New event types
- Additional agent behaviors
- UI/UX improvements for API
- WebSocket enhancements

### Low Priority

- Code refactoring
- Style improvements
- Additional examples

## Questions?

Feel free to open an issue for questions or discussions about contributions.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (CC BY-NC-SA 4.0).
