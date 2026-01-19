# Contributing to Callback Platform

Thank you for considering contributing to this project! 🎉

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template** when creating a new issue
3. **Include**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs (sanitize sensitive data!)
   - Environment details (OS, Docker version, etc.)

### Suggesting Features

1. **Open an issue** with the feature request template
2. **Describe**:
   - The problem you're trying to solve
   - Your proposed solution
   - Alternative solutions considered
   - Any implementation ideas

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**:
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed
4. **Test your changes**:
   - Ensure Docker build succeeds
   - Test callback flow end-to-end
   - Check logs for errors
5. **Commit with clear messages**:
   - Use present tense: "Add feature" not "Added feature"
   - Reference issues: "Fix #123: Resolve OAuth redirect issue"
6. **Push and create PR**:
   - Describe what changed and why
   - Link related issues
   - Add screenshots if UI changed

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/callback-platform.git
cd callback-platform

# Create .env file
cp .env.example .env
# Edit .env with your test credentials

# Start development environment
docker-compose up --build

# In another terminal, watch logs
docker logs -f callback-backend
```

## Code Style

### Python (Backend)

- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions
- Include comprehensive logging (per Rule 25)
- Handle exceptions gracefully

Example:
```python
def process_callback(visitor_phone):
    """
    Process callback request for visitor.
    
    Args:
        visitor_phone (str): Visitor's phone number in E.164 format
        
    Returns:
        dict: Result with success status and request_id
    """
    logger.info(f"Processing callback for {visitor_phone}")
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Callback processing failed: {str(e)}")
        raise
```

### JavaScript (Frontend)

- Use ES6+ features
- Add comments for complex logic
- Use meaningful variable names
- Handle errors gracefully
- Log important events to console

Example:
```javascript
async function requestCallback(phoneNumber) {
  log('info', 'Requesting callback', { phoneNumber });
  
  try {
    const response = await fetch(`${CONFIG.BACKEND_URL}/request_callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visitor_number: phoneNumber })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    log('error', 'Callback request failed', { error: error.message });
    throw error;
  }
}
```

## Testing

### Manual Testing Checklist

- [ ] Backend starts without errors
- [ ] Health endpoint returns healthy status
- [ ] Frontend loads correctly
- [ ] Social login redirects work
- [ ] Manual form submission works
- [ ] Callback is received on business phone
- [ ] SMS fallback works when call is missed
- [ ] Database stores callback records
- [ ] Logs show all events

### Adding Tests

We welcome automated tests! Consider adding:

- Unit tests for backend functions
- Integration tests for API endpoints
- Frontend JavaScript tests
- End-to-end tests for callback flow

## Documentation

When adding features, please update:

- **README.md** - User-facing documentation
- **Code comments** - For complex logic
- **Docstrings** - For Python functions
- **CHANGELOG.md** - List your changes

## Questions?

- Open a discussion on GitHub
- Check existing issues and PRs
- Review the README troubleshooting section

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Focus on what's best for the project

Thank you for contributing! 🙏

