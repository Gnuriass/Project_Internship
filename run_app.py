# run_app.py
# This script serves as the executable's entry point (wrapper).

import sys
import os
# Import Streamlit's internal CLI module
import streamlit.web.cli as stcli

def main():
    """Initializes and runs the Streamlit application."""
    
    # 1. Handle PyInstaller's temporary directory
    # When running as an EXE, files are unpacked to a temp folder.
    if getattr(sys, 'frozen', False):
        # sys._MEIPASS holds the path to the temp directory
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        # Change the current working directory to the temp path
        os.chdir(bundle_dir) 
        
    # 2. Configure arguments for Streamlit
    # We set the arguments as if we were running 'streamlit run app.py' in the terminal.
    # Note: 'app.py' MUST be included in the PyInstaller build using --add-data.
    sys.argv = [
        "streamlit", 
        "run", 
        # The Streamlit file to run. Since we chdir'd above, '.' is correct.
        "app.py", 
        # Optional: Disable dev mode for faster startup in the executable
        "--global.developmentMode=false" 
    ]
    
    # 3. Launch Streamlit's CLI main function directly
    sys.exit(stcli.main())

if __name__ == '__main__':
    main()