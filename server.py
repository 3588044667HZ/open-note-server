import socket

local_ip = '127.0.0.1'
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('10.254.254.254', 1))
    local_ip = s.getsockname()[0]
    s.close()
except Exception:
    pass

print(f' * Local:    http://127.0.0.1:5000')
print(f' * Network:  http://{local_ip}:5000')
print(f' * API base: http://{local_ip}:5000/api/')

from app import create_app
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
