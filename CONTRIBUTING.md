# Contributing to Pearls AQI Predictor

Thank you for your interest in contributing to Pearls AQI Predictor!

## Development Setup

1. **Fork and clone the repository**
```bash
git clone https://github.com/munawar123421/Pearl-AQI-Predictor.git
cd Pearl-AQI-Predictor
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run tests**
```bash
pytest tests/
```

## Making Changes

1. Create a new branch
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes

3. Run tests
```bash
pytest tests/
```

4. Commit your changes
```bash
git add .
git commit -m "Add your descriptive commit message"
```

5. Push to your fork
```bash
git push origin feature/your-feature-name
```

6. Create a Pull Request

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Maintain or improve code coverage

## Questions?

Open an issue for any questions or discussions.
