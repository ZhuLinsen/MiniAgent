# 贡献指南

感谢您对MiniAgent项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 报告问题和提出建议
- 改进文档
- 提交bug修复
- 添加新功能
- 优化性能
- 提供示例和教程

## 开发环境设置

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/miniagent.git
cd miniagent
```

2. 创建并激活虚拟环境（推荐）：

```bash
python -m venv venv
# 在Windows上
venv\Scripts\activate
# 在Linux/macOS上
source venv/bin/activate
```

3. 安装开发依赖：

```bash
pip install -r requirements.txt
```

4. 本地安装包（开发模式）：

```bash
pip install -e .
```

## 开发规范

### 代码风格

- 遵循PEP 8编码规范
- 使用类型注解
- 为所有函数和类编写文档字符串（Docstring）
- 保持代码简洁、可读、可维护

### 提交规范

提交信息应遵循以下格式：

```
<类型>: <简短描述>

<详细描述>
```

其中`<类型>`可以是：

- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码风格更改（不影响代码功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 添加测试
- `chore`: 构建过程或辅助工具变动

### 分支管理

- `main`: 主分支，保持稳定可用
- `develop`: 开发分支，最新更改
- 功能分支：从`develop`分支创建，命名为`feature/<功能名称>`
- 修复分支：从`main`分支创建，命名为`fix/<bug描述>`

## 提交Pull Request

1. 在GitHub上fork项目
2. 从您的fork创建新分支
3. 进行更改并提交
4. 推送到您的fork
5. 从您的分支向原仓库的`develop`分支提交Pull Request
6. 在PR中详细描述您的更改

## 开发环境变量

将`.env.example`复制为`.env`并填写您的API密钥：

```
OPENAI_API_KEY=your_api_key_here
```

## 测试

运行测试前，请确保您已设置API密钥或使用测试模式：

```bash
# 将在未来版本中添加
# python -m pytest tests/
```

感谢您的贡献！ 