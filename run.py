from app import create_app

app = create_app()


@app.route('/')
def index():
    return {
        "success": True,
        "message": "ZGF ERP System 正在运行",
        "api_endpoints": {
            "v1": "/api/v1",
            "v2": "/api/v2 (开发中)"
        }
    }


if __name__ == '__main__':
    app.run(debug=True, port=5000)
    # host='0.0.0.0' 允许公网访问
    # port=5000 端口号
    # debug=False 生产环境关闭调试
    # app.run(host='0.0.0.0', port=5000, debug=False)
