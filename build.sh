#!/bin/bash

# Build script for Render
set -e  # Exit on error

echo "Starting build process..."

# Install system dependencies for scikit-learn
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    libatlas-base-dev \
    liblapack-dev \
    libblas-dev \
    || echo "System dependencies might already be installed"

# Upgrade pip and install build tools
echo "Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

# Install numpy first (required by scikit-learn)
echo "Installing numpy..."
pip install numpy==1.24.3

# Install other dependencies
echo "Installing remaining dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p uploads

echo "Build completed successfully!"
