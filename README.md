# Noise Navigator Web App

A Streamlit-based interactive noise map visualization tool for Amsterdam.

## Prerequisites

• Python 3.8+ installed
• pip package manager
• Git (optional but recommended)

## Setup Instructions

### 1. Clone Repository (Optional)

If you want to clone the repository to your local machine, run the following command:

```bash
git clone https://github.com/yourusername/noise-navigator.git
cd noise-navigator
```

### 2. Create Virtual Environment

#### Windows (PowerShell)

```powershell
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\activate
```

#### Linux/macOS

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python libraries by running:

```bash
pip install -r requirements.txt
```

**For Linux/macOS users:** If you encounter errors while installing `geopandas`, you may need to install system-level dependencies first:

```bash
# Ubuntu/Debian
sudo apt-get install gdal-bin libgdal-dev

# macOS (Homebrew)
brew install gdal
```

### 4. Run the Application

Once the virtual environment is activated and dependencies are installed, start the Streamlit app by running:

```bash
streamlit run app.py
```

The app will open in your default web browser. You can interact with the noise map visualization tool from there.


## Troubleshooting

1. **Virtual Environment Activation Fails**:
   • Windows: Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` to allow script execution.
   • Ensure Python is added to your system PATH.

2. **Missing Dependencies**:
   ```bash
   pip install --force-reinstall -r requirements.txt
   ```

3. **Port Conflicts**:
   If the default port (8501) is already in use, specify a different port:
   ```bash
   streamlit run app.py --server.port 8502
   ```

## Recommended Workflow

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate   # Windows
   ```

2. Develop and test your features.

3. Commit your changes to Git.

4. Deactivate the virtual environment when finished:
   ```bash
   deactivate
   ```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

### Notes

• Replace `yourusername` in the `git clone` command with your actual GitHub username.
• Ensure all necessary data files are placed in the `data/` directory before running the app.

This `README.md` file provides clear instructions for setting up the project on both Linux/macOS and Windows, ensuring a smooth onboarding experience for other developers.