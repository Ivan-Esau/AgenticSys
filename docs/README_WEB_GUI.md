# 🚀 GitLab Agent System - Web GUI

## Overview

The Web GUI provides a modern, user-friendly interface for the GitLab Agent System, replacing the command-line interface with an intuitive web application.

## 🎯 Quick Start (Streamlit Prototype)

### 1. Install Dependencies
```bash
pip install -r requirements-webgui.txt
```

### 2. Run the Web Interface
```bash
streamlit run web_gui_prototype.py
```

### 3. Access the Application
Open your browser to: http://localhost:8501

## 📱 Features

### Current Prototype Features
- ✅ **Configuration Builder**: Visual interface for project setup
- ✅ **Real-time Monitoring**: Live execution progress tracking
- ✅ **Output Console**: Agent output streaming
- ✅ **Results Viewer**: Execution results and metrics
- ✅ **History Tracking**: Past execution records
- ✅ **Configuration Management**: Save/load configurations

### Planned Features
- ⏳ Real integration with agent system
- ⏳ WebSocket-based live streaming
- ⏳ GitLab API integration
- ⏳ Advanced analytics dashboard
- ⏳ Multi-user support
- ⏳ Scheduling system

## 🏗️ Architecture Options

### Option 1: Streamlit (Current - Rapid Prototyping)
```
Streamlit App
    ↓
Python Backend (Direct)
    ↓
Agent System
```

**Pros:**
- Quick to implement (1-2 weeks)
- Pure Python
- Built-in components
- Easy deployment

**Cons:**
- Limited UI customization
- Less scalable
- Basic real-time features

### Option 2: Full Stack (Future - Production)
```
React Frontend
    ↓ (REST + WebSocket)
FastAPI Backend
    ↓
Celery Task Queue
    ↓
Agent System
```

**Pros:**
- Full control over UI/UX
- Highly scalable
- Real-time streaming
- Production-ready

**Cons:**
- Longer development (8-12 weeks)
- More complex
- Requires frontend expertise

## 🖥️ User Interface

### Main Sections

#### 1. Configuration Panel (Sidebar)
- Project ID input
- Operation mode selection
- Tech stack configuration
- LLM provider settings
- Advanced options

#### 2. Dashboard
- Execution metrics
- Quick actions
- Recent activity
- System status

#### 3. Execution Monitor
- Real-time status
- Progress tracking
- Agent output console
- Control buttons (Start/Pause/Resume/Stop)

#### 4. Results Viewer
- File changes
- Test results
- Coverage reports
- Downloadable reports

#### 5. History
- Past executions
- Success/failure tracking
- Performance trends

## 🚀 Deployment Options

### Local Development
```bash
streamlit run web_gui_prototype.py --server.port 8501
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-webgui.txt .
RUN pip install -r requirements-webgui.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "web_gui_prototype.py"]
```

Build and run:
```bash
docker build -t gitlab-agent-gui .
docker run -p 8501:8501 gitlab-agent-gui
```

### Production Deployment (Streamlit Cloud)
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Deploy with one click

### Production Deployment (Self-hosted)
```bash
# With PM2
pm2 start "streamlit run web_gui_prototype.py" --name gitlab-agent-gui

# With systemd
# Create /etc/systemd/system/gitlab-agent-gui.service
```

## 🔧 Configuration

### Environment Variables
```bash
# .env file
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_token_here
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key
```

### Streamlit Configuration
```toml
# .streamlit/config.toml
[server]
port = 8501
headless = true

[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
textColor = "#262730"
```

## 📊 Usage Examples

### Basic Analysis
1. Enter Project ID
2. Select "Analyze Only" mode
3. Click "Start"
4. Monitor progress in real-time
5. View results when complete

### Full Implementation
1. Configure project and tech stack
2. Select "Full Implementation"
3. Configure LLM provider
4. Start execution
5. Monitor agent progress
6. Review and download results

### Resume Previous Execution
1. Select "Resume from State"
2. Upload state file
3. Continue from last checkpoint

## 🔌 Integration with Agent System

### Current (Simulated)
```python
# Simulated execution for prototype
def simulate_execution():
    # Mock agent output
    yield "Planning: Analyzing project..."
    yield "Coding: Implementing features..."
    yield "Testing: Running tests..."
```

### Future (Real Integration)
```python
# Real agent integration
async def execute_with_streaming(config):
    from src.orchestrator.supervisor import run_supervisor

    async for output in run_supervisor(**config):
        yield output  # Stream to UI
```

## 🧪 Testing

### Manual Testing
1. Run the application
2. Test all configuration options
3. Verify execution flow
4. Check results display

### Automated Testing
```python
# test_web_gui.py
import streamlit.testing as st_testing

def test_configuration():
    app = st_testing.AppTest("web_gui_prototype.py")
    app.run()

    # Test configuration
    app.text_input[0].input("123").run()
    assert app.session_state.config["project_id"] == "123"
```

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Kill existing process
lsof -i :8501
kill -9 <PID>

# Or use different port
streamlit run web_gui_prototype.py --server.port 8502
```

#### Session State Issues
Clear browser cache or use incognito mode

#### Performance Issues
- Reduce console output buffer
- Implement pagination for history
- Use caching for repeated operations

## 📈 Performance Optimization

### Streamlit Caching
```python
@st.cache_data
def load_project_data(project_id):
    # Expensive operation
    return fetch_from_gitlab(project_id)

@st.cache_resource
def get_llm_client():
    # Singleton pattern
    return LLMClient()
```

### Async Operations
```python
async def run_async_operation():
    # Use asyncio for non-blocking operations
    results = await agent.execute_async()
    return results
```

## 🔮 Future Enhancements

### Phase 1 (Current)
- ✅ Basic Streamlit prototype
- ✅ Configuration interface
- ✅ Simulated execution

### Phase 2 (Next 2-4 weeks)
- [ ] Real agent integration
- [ ] Database persistence
- [ ] WebSocket streaming
- [ ] Authentication

### Phase 3 (1-2 months)
- [ ] FastAPI backend
- [ ] React frontend
- [ ] Advanced analytics
- [ ] Multi-user support

### Phase 4 (3+ months)
- [ ] Scheduling system
- [ ] Email notifications
- [ ] API access
- [ ] Mobile app

## 📚 Documentation

- [Development Plan](WEB_GUI_DEVELOPMENT_PLAN.md) - Full development roadmap
- [Streamlit Quick Start](WEB_GUI_QUICKSTART_STREAMLIT.md) - Streamlit-specific guide
- [API Design](WEB_GUI_API_DESIGN.md) - REST and WebSocket API specs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

Same as main project

## 💬 Support

For issues or questions:
- Create an issue on GitHub
- Check existing documentation
- Contact the development team

---

**Note**: This is a prototype implementation. The production version will use React + FastAPI for better scalability and features.