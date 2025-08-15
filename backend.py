from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import glob
from pathlib import Path
import urllib.parse
# 新增导入
from fastapi import Request
from pydantic import BaseModel
from typing import List
import numpy as np
from PIL import Image
import requests
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import io
import base64
import json
import asyncio
import time

app = FastAPI()

# 进度管理器
class ProgressManager:
    def __init__(self):
        self.current_progress = 0
        self.status = "idle"  # idle, extracting, reducing, completed, error
        self.message = ""
        self.total_images = 0
        
    def reset(self):
        """重置进度状态"""
        self.current_progress = 0
        self.status = "idle"
        self.message = ""
        self.total_images = 0
        
    def update(self, progress: int, status: str, message: str, total: int = None):
        self.current_progress = progress
        self.status = status
        self.message = message
        if total is not None:
            self.total_images = total
            
    def get_status(self):
        return {
            "progress": self.current_progress,
            "status": self.status,
            "message": self.message,
            "total_images": self.total_images
        }

progress_manager = ProgressManager()

# 挂载静态文件服务
app.mount("/static", StaticFiles(directory="/tmp"), name="static")

@app.get("/")
def root():
    return {"message": "图片展示API服务正在运行", "api_docs": "/docs", "frontend": "/frontend.html"}

# 提供前端HTML文件
@app.get("/frontend.html")
def get_frontend():
    """提供前端HTML文件"""
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path, media_type="text/html")
    else:
        return JSONResponse(status_code=404, content={"error": "前端文件不存在"})

# 允许跨域，方便前后端分离开发
domains = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=domains,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/get_images")
def get_images(txt_path: str = Query(..., description="txt文件路径或图片文件夹路径")):
    if not os.path.exists(txt_path):
        return JSONResponse(status_code=404, content={"error": "路径不存在"})
    
    try:
        image_paths = []
        
        # 如果是文件夹，扫描其中的图片文件
        if os.path.isdir(txt_path):
            # 支持的图片格式
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp', '*.svg', '*.tiff', '*.tif']
            
            for ext in image_extensions:
                # 使用glob递归搜索（包括子文件夹）
                pattern = os.path.join(txt_path, '**', ext)
                image_paths.extend(glob.glob(pattern, recursive=True))
                # 也搜索大写扩展名
                pattern_upper = os.path.join(txt_path, '**', ext.upper())
                image_paths.extend(glob.glob(pattern_upper, recursive=True))
            
            # 去重并转换为相对于文件夹的路径或绝对路径
            image_paths = list(set(image_paths))
            
        # 如果是文件，按原来的逻辑读取
        elif os.path.isfile(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            # 处理每一行：如果是相对路径，转换为绝对路径
            base_dir = os.path.dirname(os.path.abspath(txt_path))
            for line in lines:
                if os.path.isabs(line):
                    # 绝对路径直接添加
                    image_paths.append(line)
                elif line.startswith('http://') or line.startswith('https://'):
                    # URL直接添加
                    image_paths.append(line)
                else:
                    # 相对路径转换为绝对路径
                    abs_path = os.path.join(base_dir, line)
                    image_paths.append(abs_path)
        
        else:
            return JSONResponse(status_code=400, content={"error": "路径必须是文件或文件夹"})
        
        # 排序
        image_paths.sort()
        
        # 将本地文件路径转换为可访问的URL
        processed_paths = []
        for path in image_paths:
            if path.startswith('http://') or path.startswith('https://'):
                # URL直接使用
                processed_paths.append(path)
            elif os.path.isfile(path):
                # 本地文件转换为静态文件URL
                # 如果路径在/tmp下，使用static服务
                if path.startswith('/tmp/'):
                    relative_path = os.path.relpath(path, '/tmp')
                    static_url = f"http://localhost:8001/static/{relative_path}"
                    processed_paths.append(static_url)
                else:
                    # 对于/tmp外的文件，使用文件服务API
                    import urllib.parse
                    encoded_path = urllib.parse.quote(path)
                    file_url = f"http://localhost:8001/file?path={encoded_path}"
                    processed_paths.append(file_url)
            else:
                # 文件不存在，但仍然添加（前端会显示错误）
                processed_paths.append(path)
        
        return {
            "images": processed_paths,
            "count": len(processed_paths),
            "type": "directory" if os.path.isdir(txt_path) else "file"
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"处理失败: {str(e)}"})

@app.get("/file")
def serve_file(path: str = Query(..., description="文件路径")):
    """提供任意路径的文件服务"""
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
    
    if not os.path.isfile(path):
        return JSONResponse(status_code=400, content={"error": "路径不是文件"})
    
    try:
        return FileResponse(path)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"文件服务失败: {str(e)}"})

# 进度查询端点
@app.get("/progress")
def get_progress():
    """获取当前进度"""
    return progress_manager.get_status()

# 服务器发送事件(SSE)进度流
@app.get("/progress/stream")
def progress_stream():
    """进度流式推送"""
    def generate():
        last_status = None
        while True:
            current_status = progress_manager.get_status()
            
            # 只在状态变化时发送
            if current_status != last_status:
                yield f"data: {json.dumps(current_status)}\n\n"
                last_status = current_status.copy()
            
            # 如果已完成或出错，停止流
            if current_status["status"] in ["completed", "error"]:
                break
                
            time.sleep(0.1)  # 100ms检查一次
    
    return StreamingResponse(generate(), media_type="text/plain")

# 新增特征可视化相关模型
class VisualizationRequest(BaseModel):
    image_paths: List[str]
    selected_indices: List[int]
    method: str = "pca"  # "pca" 或 "tsne"

def extract_image_features(image_path: str, target_size=(64, 64)):
    """提取图片特征（缩小分辨率加速）"""
    try:
        if image_path.startswith('http://') or image_path.startswith('https://'):
            # 检查是否是指向本服务器的URL
            if 'localhost:8001/file?path=' in image_path:
                # 从URL中提取本地文件路径
                from urllib.parse import unquote
                local_path = image_path.split('path=')[1]
                local_path = unquote(local_path)
                image = Image.open(local_path)
            else:
                # 处理外部URL图片
                response = requests.get(image_path, timeout=30)
                image = Image.open(io.BytesIO(response.content))
        else:
            # 直接处理本地文件
            image = Image.open(image_path)
        
        # 转换为RGB并调整大小
        image = image.convert('RGB')
        image = image.resize(target_size)
        
        # 转换为numpy数组并展平
        features = np.array(image).flatten() / 255.0
        
        return features
        
    except Exception as e:
        print(f"提取特征失败 {image_path}: {str(e)}")
        # 返回零向量作为默认特征
        return np.zeros(target_size[0] * target_size[1] * 3)

@app.post("/visualize_features")
async def visualize_features(request: VisualizationRequest):
    """生成图片特征的3D可视化数据"""
    print(f"🎨 收到特征可视化请求")
    print(f"   - 图片数量: {len(request.image_paths)}")
    print(f"   - 选中图片数量: {len(request.selected_indices)}")
    print(f"   - 降维方法: {request.method}")
    
    try:
        # 重置进度状态
        progress_manager.reset()
        total_images = len(request.image_paths)
        progress_manager.update(0, "extracting", "开始提取图片特征...", total_images)
        
        # 给用户一点时间看到开始状态
        await asyncio.sleep(0.1)
        
        # 提取所有图片的特征
        features = []
        valid_indices = []
        
        print(f"🔍 开始提取特征...")
        
        for i, image_path in enumerate(request.image_paths):
            # 更新进度 - 特征提取阶段占70%
            progress = int((i / total_images) * 70)
            progress_manager.update(progress, "extracting", f"提取特征中... ({i+1}/{total_images})", total_images)
            
            # 给前端足够时间获取进度状态
            if i % 3 == 0:  # 每处理3张图片就让步一次，更频繁
                await asyncio.sleep(0.2)  # 增加等待时间，确保前端能轮询到
                print(f"  🔄 进度更新: {progress}% - {i+1}/{total_images}")
            
            if i % 10 == 0 or i == total_images - 1:  # 更频繁的日志输出
                print(f"  进度: {i+1}/{total_images} ({progress}%)")
            feature = extract_image_features(image_path)
            if feature is not None:
                features.append(feature)
                valid_indices.append(i)
        
        print(f"✅ 成功提取 {len(features)} 个图片的特征")
        
        if len(features) == 0:
            progress_manager.update(0, "error", "无法提取任何图片特征", total_images)
            print("❌ 无法提取任何图片特征")
            return JSONResponse(status_code=400, content={"error": "无法提取任何图片特征"})
        
        features = np.array(features)
        print(f"📊 特征矩阵形状: {features.shape}")
        
        # 降维阶段 70%-95%
        progress_manager.update(75, "reducing", "准备降维算法...", total_images)
        await asyncio.sleep(0.3)  # 增加等待时间，让前端能获取到这个状态
        print(f"  🔄 进度更新: 75% - 准备降维算法")
        
        use_tsne = request.method.lower() == "tsne" and len(features) <= 200
        if request.method.lower() == "tsne" and len(features) > 200:
            print("⚠️ 样本数过多，自动切换为PCA降维")
        print(f"🔄 开始{'t-SNE' if use_tsne else 'PCA'}降维...")
        
        progress_manager.update(80, "reducing", f"初始化{'t-SNE' if use_tsne else 'PCA'}算法...", total_images)
        await asyncio.sleep(0.3)  # 增加等待时间
        print(f"  🔄 进度更新: 80% - 初始化算法")
        
        if use_tsne:
            # 如果特征维度太高，先用PCA降到50维
            if features.shape[1] > 50:
                print("   先用PCA降到50维")
                progress_manager.update(85, "reducing", "先用PCA预处理...", total_images)
                await asyncio.sleep(0.3)
                print(f"  🔄 进度更新: 85% - PCA预处理")
                pca_pre = PCA(n_components=50)
                features = pca_pre.fit_transform(features)
            
            progress_manager.update(90, "reducing", "执行t-SNE降维（这可能需要较长时间）...", total_images)
            await asyncio.sleep(0.3)
            print(f"  🔄 进度更新: 90% - t-SNE降维")
            reducer = TSNE(n_components=3, random_state=42, perplexity=min(30, len(features)-1))
        else:  # PCA
            progress_manager.update(85, "reducing", "执行PCA降维...", total_images)
            await asyncio.sleep(0.3)
            print(f"  🔄 进度更新: 85% - PCA降维")
            reducer = PCA(n_components=3)
        
        # 降维到3维
        progress_manager.update(92, "reducing", "计算3D坐标...", total_images)
        await asyncio.sleep(0.3)
        print(f"  🔄 进度更新: 92% - 计算3D坐标")
        reduced_features = reducer.fit_transform(features)
        print(f"✅ 降维完成，3D特征形状: {reduced_features.shape}")
        
        # 准备可视化数据 95%-99%
        progress_manager.update(95, "reducing", "生成可视化数据...", total_images)
        await asyncio.sleep(0.3)
        print(f"  🔄 进度更新: 95% - 生成可视化数据")
        
        visualization_data = []
        selected_count = 0
        for i, (original_idx, coords) in enumerate(zip(valid_indices, reduced_features)):
            # 更新进度 - 数据组装阶段 95%-99%
            if i % max(1, len(reduced_features) // 5) == 0:  # 更频繁更新
                progress = 95 + int((i / len(reduced_features)) * 4)
                progress_manager.update(progress, "reducing", f"组装可视化数据... ({i+1}/{len(reduced_features)})", total_images)
                await asyncio.sleep(0.2)  # 每次更新后等待
                print(f"  🔄 进度更新: {progress}% - 组装数据 {i+1}/{len(reduced_features)}")
            
            is_selected = original_idx in request.selected_indices
            if is_selected:
                selected_count += 1
                print(f"  选中图片 {original_idx}: {request.image_paths[original_idx][:50]}...")
            visualization_data.append({
                "x": float(coords[0]),
                "y": float(coords[1]), 
                "z": float(coords[2]),
                "image_path": request.image_paths[original_idx],
                "image_index": original_idx,
                "selected": is_selected
            })
        
        print(f"🎯 生成可视化数据: {len(visualization_data)} 个点，其中 {selected_count} 个已选择")
        
        # 完成
        progress_manager.update(100, "completed", f"完成！处理了 {len(features)} 张图片", total_images)
        
        result = {
            "success": True,
            "method": request.method,
            "data": visualization_data,
            "total_images": len(request.image_paths),
            "processed_images": len(features)
        }
        
        print(f"✅ 返回结果: 成功处理 {len(features)} 张图片")
        return result
        
    except Exception as e:
        progress_manager.update(0, "error", f"处理失败: {str(e)}", total_images)
        print(f"❌ 特征可视化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"特征可视化失败: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
