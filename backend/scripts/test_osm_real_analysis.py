"""
使用OSM真实数据测试完整分析流程
"""

import requests
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api"
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data_osm"

def create_project():
    """创建测试项目"""
    print("1. 创建项目...")
    response = requests.post(
        f"{BASE_URL}/projects",
        json={
            "name": "osm_test",
            "description": "OSM真实数据测试项目"
        }
    )
    response.raise_for_status()
    result = response.json()
    project_id = result["data"]["id"]
    print(f"   项目已创建: {project_id}")
    return project_id


def upload_file(project_id, data_type, file_path):
    """上传数据文件"""
    print(f"   上传 {data_type}: {file_path.name}")
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/geo+json')}
        data = {'description': f'{data_type} data'}
        response = requests.post(
            f"{BASE_URL}/projects/{project_id}/data/{data_type}",
            files=files,
            data=data
        )
        response.raise_for_status()
    print(f"      [OK] {data_type} 上传成功")


def upload_all_data(project_id):
    """上传所有数据文件"""
    print("\n2. 上传数据文件...")
    
    # 只上传必需的矢量数据
    data_files = {
        'boundary': TEST_DATA_DIR / 'boundary.geojson',
        'poi': TEST_DATA_DIR / 'poi.geojson',
        'roads': TEST_DATA_DIR / 'roads.geojson',
        'water_bodies': TEST_DATA_DIR / 'water_bodies.geojson',
    }
    
    for data_type, file_path in data_files.items():
        if file_path.exists():
            try:
                upload_file(project_id, data_type, file_path)
            except Exception as e:
                print(f"      [WARN] {data_type} 上传失败: {e}")
        else:
            print(f"      [WARN] {data_type} 文件不存在: {file_path}")


def start_analysis(project_id):
    """启动分析"""
    print("\n3. 启动分析...")
    response = requests.post(
        f"{BASE_URL}/projects/{project_id}/analyze",
        json={
            "grid_size": 100,
            "functions": ["商业", "居住", "工业", "绿地休闲", "公共服务"]
        }
    )
    response.raise_for_status()
    print("   分析任务已启动")


def wait_for_completion(project_id, timeout=300):
    """等待分析完成"""
    print("\n4. 等待分析完成...")
    start_time = time.time()
    
    while True:
        response = requests.get(f"{BASE_URL}/projects/{project_id}")
        response.raise_for_status()
        result = response.json()
        project = result["data"]
        
        status = project.get('analysis_status', 'pending')
        progress = project.get('analysis_progress', 0)
        
        print(f"   状态: {status} ({progress}%)", end='\r')
        
        if status == 'completed':
            print(f"\n   [OK] 分析完成！")
            return True
        elif status == 'failed':
            error = project.get('error_message', '未知错误')
            print(f"\n   [ERROR] 分析失败: {error}")
            return False
        elif time.time() - start_time > timeout:
            print(f"\n   [WARN] 超时 ({timeout}秒)")
            return False
        
        time.sleep(2)


def check_results(project_id):
    """检查分析结果"""
    print("\n5. 检查分析结果...")
    
    # 获取项目信息
    response = requests.get(f"{BASE_URL}/projects/{project_id}")
    response.raise_for_status()
    result = response.json()
    project = result["data"]
    
    print(f"   项目ID: {project['id']}")
    print(f"   项目名称: {project['name']}")
    print(f"   分析状态: {project['analysis_status']}")
    
    # 获取结果统计
    response = requests.get(f"{BASE_URL}/projects/{project_id}/results")
    response.raise_for_status()
    results = response.json()
    
    if 'statistics' in results:
        stats = results['statistics']
        print(f"\n   网格单元数: {stats.get('total_units', 0)}")
        print(f"   功能分布:")
        for func, count in stats.get('function_counts', {}).items():
            print(f"      {func}: {count}个单元")
    
    # 测试问答
    print("\n6. 测试问答功能...")
    test_questions = [
        "哪里适合商业开发？",
        "推荐居住用地",
        "适合工业的区域"
    ]
    
    for question in test_questions:
        response = requests.post(
            f"{BASE_URL}/projects/{project_id}/qa",
            json={"question": question}
        )
        if response.status_code == 200:
            answer = response.json()
            print(f"\n   Q: {question}")
            print(f"   A: {answer.get('answer', '无回答')[:100]}...")
        else:
            print(f"\n   Q: {question}")
            print(f"   [ERROR] 错误: {response.status_code}")


def main():
    """主流程"""
    print("=" * 60)
    print("OSM真实数据完整分析测试")
    print("=" * 60)
    
    try:
        # 创建项目
        project_id = create_project()
        
        # 上传数据
        upload_all_data(project_id)
        
        # 启动分析
        start_analysis(project_id)
        
        # 等待完成
        if wait_for_completion(project_id):
            # 检查结果
            check_results(project_id)
            print("\n" + "=" * 60)
            print("测试完成！")
            print(f"项目ID: {project_id}")
            print(f"前端查看: http://localhost:5500/?project={project_id}")
            print("=" * 60)
        else:
            print("\n分析未能完成")
            
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
