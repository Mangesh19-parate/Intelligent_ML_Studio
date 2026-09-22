"""
Unified Worker Entrypoint for ML Studio Background Task Processing.
Delegates to the durable task worker daemon.
"""

from app.tasks.worker import main

if __name__ == "__main__":
    main()
