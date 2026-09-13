# Contributing to TrustMesh

Thank you for your interest in contributing to TrustMesh! 🎉

TrustMesh is an open-source project building the reputation layer for AI agents. We welcome contributions of all kinds.

## 🤝 How to Contribute

### Reporting Bugs 🐛

Found a bug? Please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version)

### Suggesting Features 💡

Have an idea? Open an issue with:
- Clear description of the feature
- Why it would be useful
- Possible implementation approach

### Code Contributions 🔧

1. **Fork the repository**
   ```bash
   git clone https://github.com/ashishjsharda/trustmesh.git
   cd trustmesh
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write clear, commented code
   - Follow existing code style
   - Test your changes locally

4. **Test thoroughly**
   ```bash
   python main.py
   # Test your changes via API at http://localhost:8000/docs
   ```

5. **Commit with a clear message**
   ```bash
   git commit -m "Add: brief description of what you added"
   ```

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 What We Need Help With

### High Priority
- [ ] **Testing**: Try breaking things, report bugs
- [ ] **Documentation**: Improve clarity, add examples
- [ ] **TypeScript SDK**: Port the Python SDK to TypeScript
- [ ] **A2A Integration**: Build middleware for A2A protocol
- [ ] **Web Dashboard**: Build a UI to visualize trust scores

### Medium Priority
- [ ] **PostgreSQL Support**: Replace SQLite for production
- [ ] **Rate Limiting**: Implement proper rate limiting
- [ ] **Authentication**: Improve security
- [ ] **Error Handling**: Better error messages
- [ ] **Logging**: Add comprehensive logging

### Nice to Have
- [ ] **Rust SDK**: High-performance SDK
- [ ] **CLI Tool**: Command-line interface
- [ ] **Docker**: Containerization
- [ ] **Benchmarks**: Performance testing
- [ ] **More Examples**: Real-world integration examples

## 🎨 Code Style

- Use clear, descriptive variable names
- Add comments for complex logic
- Keep functions focused and small
- Follow PEP 8 for Python code

## 🧪 Testing

Currently, testing is manual via the `/docs` API interface. We need help setting up:
- Unit tests (pytest)
- Integration tests
- CI/CD pipeline

## 📝 Documentation

Good documentation is critical! When contributing:
- Update README if you change functionality
- Add docstrings to functions
- Include usage examples
- Explain "why" not just "what"

## 🚀 Development Setup

```bash
# Clone and setup
git clone https://github.com/ashishjsharda/trustmesh.git
cd trustmesh

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

## 💬 Communication

- **Issues**: For bugs, features, questions
- **Pull Requests**: For code contributions
- **Discussions**: For open-ended conversations (coming soon)

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Every contribution matters, no matter how small. Thank you for helping build the trust layer for AI agents!

---

**Questions?** Open an issue or reach out to [@ashishjsharda](https://github.com/ashishjsharda)