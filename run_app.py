import sys
import os
import streamlit.web.cli as stcli

def main():

    if getattr(sys, 'frozen', False):
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        os.chdir(bundle_dir) 
        
    sys.argv = [
        "streamlit", 
        "run", 
        "app.py", 
        "--global.developmentMode=false" 
    ]
    
    sys.exit(stcli.main())

if __name__ == '__main__':
    main()