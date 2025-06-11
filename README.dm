Install Guide for Windows:

1. Open Terminal (Win + X):
    winget install Python.Python.3

2. Create a Folder for the Project and change your Directory to that.

3. Clone Reposetory (if no Git isntalled on your Computer use this Guide: https://git-scm.com/downloads/win
                        or use the Terminal Command: winget install Git.Git)
    git clone https://github.com/dein-benutzername/dein-repo.git
    cd dein-repo

4. Change the Directory in your Terminal to the Folder and create the Virtual Enviorment:
    python -m venv venv

5. Activate the venv (if successful you'll see (venv) in your Prompt):
    .\venv\Scripts\activate

6. Install all the Dependencys for the Code:
    pip install --upgrade pip
    pip install -r requirements.txt