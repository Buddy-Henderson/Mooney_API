import os
import subprocess
import sys
import venv
import platform

def run_command(command, error_message):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {error_message}")
        print(e.stderr)
        return False

def create_virtualenv(venv_path):
    """Create a virtual environment if it doesn't exist."""
    if not os.path.exists(venv_path):
        print(f"Creating virtual environment at {venv_path}...")
        venv.create(venv_path, with_pip=True)
    else:
        print(f"Virtual environment already exists at {venv_path}")

def get_pip_path(venv_path):
    """Get the path to pip in the virtual environment."""
    if platform.system() == "Windows":
        return os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        return os.path.join(venv_path, "bin", "pip")

def get_python_path(venv_path):
    """Get the path to Python in the virtual environment."""
    if platform.system() == "Windows":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else:
        return os.path.join(venv_path, "bin", "python")

def install_dependencies(venv_path):
    """Install required dependencies in the virtual environment."""
    pip_path = get_pip_path(venv_path)
    
    # Upgrade pip
    print("Upgrading pip...")
    run_command(f'"{pip_path}" install --upgrade pip', "Failed to upgrade pip")
    
    # List of dependencies
    dependencies = ["flask", "ccxt", "requests", "pandas", "ta", "numpy"]
    
    # Install each dependency
    for dep in dependencies:
        print(f"Installing {dep}...")
        if not run_command(f'"{pip_path}" install {dep}', f"Failed to install {dep}"):
            return False
    
    # Verify installations
    print("Verifying installed packages...")
    result = run_command(f'"{pip_path}" list', "Failed to list installed packages")
    if result:
        print("Dependencies installed successfully!")
    return result

def main():
    """Main function to set up the virtual environment and install dependencies."""
    # Define virtual environment path
    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(project_dir, "venv")
    
    # Create virtual environment
    create_virtualenv(venv_path)
    
    # Install dependencies
    if install_dependencies(venv_path):
        python_path = get_python_path(venv_path)
        print(f"\nSetup complete! To activate the virtual environment:")
        if platform.system() == "Windows":
            print(f"cd {project_dir}")
            print(f"venv\\Scripts\\activate")
        else:
            print(f"cd {project_dir}")
            print(f"source venv/bin/activate")
        print(f"\nTo run the API:")
        print(f'"{python_path}" app.py"')
    else:
        print("Setup failed. Check the errors above and try again.")

if __name__ == "__main__":
    # Ensure Python version is 3.8 or higher
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        sys.exit(1)
    main()