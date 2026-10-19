"""
知识问答路由
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from pathlib import Path
import logging
import json

from api.project_manager import ProjectManager
from api.schemas import success_response
from kg.knowledge_graph_builder import SpatialKnowledgeGraph, NodeType, RelationType
from kg.nlg_generator import NaturalLanguageGenerator

logger = logging.getLogger(__name__)

router = APIRouter()
project_manager = ProjectManager()

# 查询类问题的默认适宜性阈值（数据稀疏时得分普遍偏低，阈值不宜过高）
DEFAULT_MIN_SCORE = 0.3

# 功能关键词 → 规范功能名（用于从自然语言问题中抽取功能类型）
FUNCTION_KEYWORDS = {
    "居住": ["居住", "住宅", "居住区", "residential"],
    "商业": ["商业", "商场", "商圈", "零售", "餐饮", "购物", "commercial"],
    "办公": ["办公", "商务", "写字楼", "office"],
    "工业": ["工业", "厂房", "制造", "industrial"],
    "公共服务": ["公共服务", "公共设施", "学校", "医院", "教育", "医疗", "public"],
    "绿地休闲": ["绿地", "公园", "休闲", "游憩", "广场", "green"],
    "综合": ["综合", "混合", "mixed"],
}

class QuestionType(str):
    """问题类型"""
    EXPLAIN = "explain"  # 解释单元适宜性
    QUERY = "query"  # 查询适宜区域
    COMPARE = "compare"  # 对比单元
    OVERVIEW = "overview"  # 整体概览

class QARequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, max_length=500, description="问题")
    question_type: Optional[str] = Field(None, description="问题类型（可选，自动识别）")
    unit_id: Optional[str] = Field(None, description="单元ID（针对特定单元的问题）")
    function_type: Optional[str] = Field(None, description="功能类型（查询类问题）")
    unit_ids: Optional[List[str]] = Field(None, description="单元ID列表（对比问题）")

class QAResponse(BaseModel):
    """问答响应"""
    question: str
    answer: str
    question_type: str
    related_units: Optional[List[str]] = None
    metadata: Optional[Dict] = None

@router.post("/projects/{project_id}/qa", response_model=dict)
async def ask_question(project_id: str, request: QARequest):
    """
    知识图谱问答
    
    - **project_id**: 项目ID
    - **question**: 自然语言问题
    - **question_type**: 问题类型（可选，自动识别）
    - **unit_id**: 单元ID（针对特定单元）
    - **function_type**: 功能类型（查询适宜区域）
    - **unit_ids**: 单元ID列表（对比多个单元）
    
    支持的问题类型：
    - explain: 解释单元的适宜性，如"为什么单元A适合居住？"
    - query: 查询适宜的区域，如"哪些区域适合商业？"
    - compare: 对比多个单元，如"对比单元A和B"
    - overview: 整体统计概览，如"整体分析结果如何？"
    """
    # 验证项目是否存在
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查分析是否完成
    if project.get("analysis_status") != "completed":
        raise HTTPException(status_code=400, detail="项目尚未完成分析，无法进行问答")
    
    try:
        # 加载知识图谱对象（NLG 需要 SpatialKnowledgeGraph 实例，而不是原始 dict）
        results_dir = project_manager.get_project_path(project_id, "results")
        kg_file = results_dir / "knowledge_graph.json"
        
        if not kg_file.exists():
            raise HTTPException(status_code=404, detail="知识图谱文件不存在")
        
        kg = SpatialKnowledgeGraph.load_from_file(str(kg_file))
        nlg = NaturalLanguageGenerator(kg)
        
        # 识别问题类型（如果未指定）
        question_type = request.question_type
        if not question_type:
            question_type = _detect_question_type(request.question, request)
        
        answer = None
        related_units = []
        metadata = {}
        
        if question_type == "explain":
            # 解释单元适宜性
            import re
            unit_id = request.unit_id
            
            # 如果没有显式提供unit_id，从问题文本中提取
            # 注意：使用 [a-zA-Z0-9_] 而非 \w，避免 Python 3 中 \w 匹配中文字符
            if not unit_id:
                unit_match = re.search(r'(?:单元|网格\s*)?([A-Za-z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+)', request.question)
                if unit_match:
                    unit_id = unit_match.group(1)
            
            if not unit_id:
                raise HTTPException(status_code=400, detail="解释问题需要提供unit_id或在问题中指定单元")
            
            # 功能类型：显式指定 > 从问题提取 > 该单元主导功能
            function_type = (request.function_type
                             or _extract_function_from_question(request.question)
                             or kg.get_unit_dominant_function(unit_id))
            if not function_type:
                raise HTTPException(status_code=404, detail=f"未找到单元{unit_id}或无法确定功能类型")
            
            answer = nlg.explain_unit_suitability(unit_id, function_type)
            related_units = [unit_id]
            metadata = {"function_type": function_type}
        
        elif question_type == "query":
            # 查询适宜区域
            function_type = request.function_type or _extract_function_from_question(request.question)
            if not function_type:
                raise HTTPException(status_code=400, detail="查询问题需要指定功能类型")
            
            answer = nlg.find_suitable_regions(function_type, min_score=DEFAULT_MIN_SCORE)
            related_units = [uid for uid, _ in kg.find_suitable_units(function_type, DEFAULT_MIN_SCORE)]
            metadata = {"function_type": function_type, "count": len(related_units)}
        
        elif question_type == "compare":
            # 对比单元
            if not request.unit_ids or len(request.unit_ids) < 2:
                raise HTTPException(status_code=400, detail="对比问题需要提供至少2个单元ID")
            
            function_type = request.function_type or _extract_function_from_question(request.question) or "综合"
            answer = nlg.compare_units(request.unit_ids, function_type)
            related_units = request.unit_ids
            metadata = {"compared_units": request.unit_ids, "function_type": function_type}
        
        elif question_type == "overview":
            # 整体概览：由知识图谱重建 单元→主导功能 映射
            all_unit_nodes = kg.get_nodes_by_type(NodeType.UNIT)
            recommendations = {
                node.id: kg.get_unit_dominant_function(node.id)
                for node in all_unit_nodes
            }
            recommendations = {k: v for k, v in recommendations.items() if v}
            answer = nlg.generate_summary(recommendations)
            related_units = list(recommendations.keys())
            metadata = {
                "total_units": len(all_unit_nodes),
                "units_with_function": len(recommendations),
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的问题类型: {question_type}")
        
        return success_response(
            data={
                "question": request.question,
                "answer": answer,
                "question_type": question_type,
                "related_units": related_units,
                "metadata": metadata
            },
            message="问答成功"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"问答异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/projects/{project_id}/knowledge-graph", response_model=dict)
async def get_knowledge_graph(project_id: str):
    """
    获取知识图谱结构
    
    - **project_id**: 项目ID
    
    返回完整的知识图谱JSON，可用于前端可视化
    """
    # 验证项目是否存在
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查分析是否完成
    if project.get("analysis_status") != "completed":
        raise HTTPException(status_code=400, detail="项目尚未完成分析")
    
    try:
        results_dir = project_manager.get_project_path(project_id, "results")
        kg_file = results_dir / "knowledge_graph.json"
        
        if not kg_file.exists():
            raise HTTPException(status_code=404, detail="知识图谱文件不存在")
        
        kg = SpatialKnowledgeGraph.load_from_file(str(kg_file))
        kg_data = kg.to_dict()
        
        # 统计信息
        unit_nodes = kg.get_nodes_by_type(NodeType.UNIT)
        function_types = sorted(set(
            kg.get_unit_dominant_function(node.id)
            for node in unit_nodes
            if kg.get_unit_dominant_function(node.id)
        ))
        stats = {
            "node_count": len(kg_data.get("nodes", [])),
            "edge_count": len(kg_data.get("relations", [])),
            "unit_count": len(unit_nodes),
            "function_types": function_types
        }
        
        return success_response(
            data={
                "knowledge_graph": kg_data,
                "statistics": stats
            },
            message="查询成功"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"获取知识图谱异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

def _detect_question_type(question: str, request: QARequest) -> str:
    """检测问题类型

    逻辑顺序：
    1. compare — 显式请求或关键词触发
    2. explain — 指定了 unit_id 或问题中包含单元ID且是解释类问题
    3. query   — 既能提取功能类型，又有查询意图（关键词或 request.function_type）
    4. overview — 其余所有情况（含"多少个适宜的位置"等无功能类型的泛查询）
    """
    import re
    question_lower = question.lower()

    # ---- 对比类 ----
    if request.unit_ids and len(request.unit_ids) >= 2:
        return "compare"
    if any(kw in question_lower for kw in ["对比", "比较", "差异"]):
        return "compare"

    # ---- 解释类 ----
    if request.unit_id:
        return "explain"
    
    # 从问题文本中提取单元ID（支持多种格式：U_0_0, UNIT_0001, 单元 U_0_0 等）
    # 注意：使用 [a-zA-Z0-9_] 而非 \w，避免 Python 3 中 \w 匹配中文字符
    unit_match = re.search(r'(?:单元|网格\s*)?([A-Za-z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+)', question)
    if unit_match and any(kw in question for kw in ["为什么", "原因", "解释", "分析", "适合"]):
        # 如果问题中包含单元ID和解释类关键词，识别为explain类型
        return "explain"

    # ---- 查询类 ----
    # 关键修正：仅当能确定功能类型时才走 query，否则 400
    function_type = request.function_type or _extract_function_from_question(question)
    if function_type:
        return "query"

    # ---- 概览类（兜底） ----
    return "overview"

def _extract_function_from_question(question: str) -> Optional[str]:
    """从问题中提取功能类型（返回规范功能名）"""
    for function_type, keywords in FUNCTION_KEYWORDS.items():
        if any(keyword in question for keyword in keywords):
            return function_type
    
    return None