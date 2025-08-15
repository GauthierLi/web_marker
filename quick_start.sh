#!/bin/bash

# 简化版启动脚本 - 快速启动图片展示系统

echo "🖼️  启动图片展示系统..."

# 检查基本文件
if [[ ! -f "backend.py" ]]; then
    echo "❌ 错误: 找不到 backend.py 文件"
    echo "请在包含项目文件的目录中运行此脚本"
    exit 1
fi

if [[ ! -f "frontend.html" ]]; then
    echo "❌ 错误: 找不到 frontend.html 文件"
    exit 1
fi

# 安装依赖（如果需要）
echo "📦 检查依赖..."
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "📦 安装依赖: FastAPI 和 Uvicorn..."
    pip3 install fastapi uvicorn python-multipart
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请检查网络连接或Python环境"
        exit 1
    fi
}

# 终止已有的服务
echo "🔄 清理旧进程..."
pkill -f "backend.py" 2>/dev/null || true
pkill -f "uvicorn.*backend" 2>/dev/null || true
sleep 1

# 创建演示文件（如果不存在）
if [[ ! -f "demo_images.txt" ]]; then
    echo "📝 创建演示文件..."
    cat > demo_images.txt << 'EOF'
https://picsum.photos/400/300?random=1
https://picsum.photos/400/300?random=2
https://picsum.photos/400/300?random=3
https://picsum.photos/400/300?random=4
https://picsum.photos/400/300?random=5
https://picsum.photos/400/300?random=6
EOF
fi

echo ""
echo "🚀 启动服务器..."
echo "================================"
echo "🌐 前端地址: http://localhost:8001/frontend.html"
echo "📚 API文档:  http://localhost:8001/docs"
echo "📁 演示文件: $(pwd)/demo_images.txt"
echo "================================"
echo ""
echo "💡 使用说明:"
echo "   1. 在浏览器中打开前端地址"
echo "   2. 输入图片文件夹路径或txt文件路径"
echo "   3. 或者直接输入: $(pwd)/demo_images.txt"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "================================"
echo ""

# 启动后端
python3 backend.py
