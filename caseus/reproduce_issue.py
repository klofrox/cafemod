
import sys
import os

# Go up one level to find 'caseus' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import caseus.packets.serverbound as serverbound
    
    print("CafeRefreshPacket in serverbound module:", hasattr(serverbound, 'CafeRefreshPacket'))
    
    # List all attributes to see what is there
    print("serverbound attributes matching 'Cafe':", [x for x in dir(serverbound) if 'Cafe' in x])

except Exception as e:
    print("Error:", e)
