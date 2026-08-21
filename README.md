# AI Image Detector

A full-stack ML web application for detecting AI-generated images.

## Project Structure

```
ai-image-detector/
├── model_training/       # Colab notebooks + training scripts
├── backend/              # FastAPI server
├── frontend/             # React application
├── data/                 # Dataset (gitignored — too large for GitHub)
└── README.md
```

## Overview

This project trains a model to distinguish AI-generated images from real ones, then serves it via a FastAPI backend with a React frontend.

- **`model_training/`** — Training pipelines (Jupyter/Colab notebooks, Python scripts).
- **`backend/`** — FastAPI service exposing the trained model.
- **`frontend/`** — React UI for uploading images and viewing predictions.
- **`data/`** — Local dataset (kept out of version control).

## Setup

See the README in each subfolder for component-specific setup instructions.
