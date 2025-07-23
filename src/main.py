"""
Main entry point for Xero Contact Manager Streamlit Application
===============================================================

Run this file to start the Streamlit web interface.
"""

import subprocess
import sys
import os

def run_streamlit_app():
    """Run the Streamlit application."""
    try:
        # Get the directory of this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Path to the streamlit app
        app_path = os.path.join(current_dir, "streamlit_app.py")
        
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", app_path,
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error running application: {str(e)}")
        print("\nTo run manually, use:")
        print("streamlit run streamlit_app.py")

if __name__ == "__main__":
    print("🚀 Starting Xero Contact Manager...")
    print("📝 This will open in your web browser at http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the application\n")
    
    run_streamlit_app()