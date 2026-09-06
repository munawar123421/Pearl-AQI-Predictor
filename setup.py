"""Setup script for Pearls AQI Predictor."""

from setuptools import setup, find_packages

setup(
    name="pearls-aqi-predictor",
    version="1.0.0",
    description="Air Quality Index prediction and forecasting platform",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Pearl AQI Team",
    url="https://github.com/munawar123421/Pearl-AQI-Predictor",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
        "pandas>=2.1.0",
        "numpy>=1.26.0",
        "scikit-learn>=1.3.0",
        "tensorflow>=2.15.0",
        "fastapi>=0.109.0",
        "uvicorn>=0.25.0",
        "streamlit>=1.29.0",
        "requests>=2.31.0",
        "click>=8.1.0",
        "structlog>=24.1.0",
        "plotly>=5.18.0",
        "altair>=5.2.0",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
            "isort>=5.13.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
