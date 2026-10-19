"""
测试FastAPI服务器启动
"""
import sys
sys.path.insert(0, ".")

try:
    from api import main
    print("[OK] API模块导入成功")
    
    from api.routes import project_routes, data_routes, analysis_routes, qa_routes
    print("[OK] 所有路由模块导入成功")
    
    print("\n服务器配置:")
    print(f"  标题: {main.app.title}")
    print(f"  版本: {main.app.version}")
    print(f"  文档: /docs")
    
    print("\n注册的路由:")
    for route in main.app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            print(f"  {methods:10} {route.path}")
    
    print("\n[OK] API服务器配置正常，可以启动")
    print("\n启动命令:")
    print("  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
    
except Exception as e:
    print(f"[ERROR] 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)