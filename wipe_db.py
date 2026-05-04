import os
import sys

# Add backend directory to path so we can import modules like config, graph_store, etc.
backend_path = os.path.join(os.getcwd(), "backend")
sys.path.append(backend_path)

from graph_store import get_driver

def wipe():
    driver = get_driver()
    if not driver:
        print("Driver not available")
        return
    try:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("Neo4j database wiped.")
    except Exception as e:
        print(f"Error wiping Neo4j: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    wipe()
