// DOM元素
const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const webSearchToggle = document.getElementById('web-search');
const searchStatus = document.getElementById('search-status');
const resultsContainer = document.getElementById('resultsContainer');

// 新增结果区域DOM元素
const vectorResultsContainer = document.getElementById('vectorResultsContainer');
const databaseResultsContainer = document.getElementById('databaseResultsContainer');

// 联网搜索状态
let webSearchEnabled = false;

// 后端API地址
const API_BASE_URL = 'http://localhost:5000';  // 确保与后端运行地址一致

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 监听联网搜索开关变化
    webSearchToggle.addEventListener('change', toggleWebSearch);
    
    // 发送按钮点击事件
    sendBtn.addEventListener('click', sendMessage);
    
    // 输入框回车事件
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // 测试后端连接
    testBackendConnection();
});

// 测试后端连接
function testBackendConnection() {
    fetch(`${API_BASE_URL}/log`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: '前端初始化',
            details: '测试后端连接',
            web_search: false
        })
    })
    .then(response => {
        if (response.ok) {
            console.log('后端连接正常');
        } else {
            handleConnectionError();
        }
    })
    .catch(error => {
        handleConnectionError();
    });
}

// 处理连接错误
function handleConnectionError() {
    const errorMsg = "无法连接到后端服务，请确保后端已运行在 http://localhost:5000";
    console.error(errorMsg);
    addMessage(errorMsg, 'ai');
    
    // 禁用发送功能
    sendBtn.disabled = true;
    userInput.disabled = true;
    userInput.placeholder = "后端服务未连接";
}

// 切换联网搜索状态
function toggleWebSearch() {
    webSearchEnabled = webSearchToggle.checked;
    searchStatus.textContent = webSearchEnabled ? '已开启' : '已关闭';
    
    // 发送日志到后端
    const action = webSearchEnabled ? '开启联网搜索' : '关闭联网搜索';
    sendLog(action);
    
    // 更新搜索结果区域提示
    if (!webSearchEnabled) {
        resultsContainer.innerHTML = '<p>开启联网搜索后，相关搜索结果将显示在这里</p>';
    }
}

// 发送消息
function sendMessage() {
    const question = userInput.value.trim();
    if (!question) return;
    
    // 在聊天历史中添加用户消息
    addMessage(question, 'user');
    
    // 清空输入框并禁用发送按钮
    userInput.value = '';
    sendBtn.disabled = true;
    userInput.disabled = true;
    
    // 显示加载状态
    addMessage('思考中...', 'ai', true);
    
    // 清空所有结果区域
    resultsContainer.innerHTML = '';
    vectorResultsContainer.innerHTML = '';
    databaseResultsContainer.innerHTML = '';
    
    // 发送请求到后端
    fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            question: question,
            web_search: webSearchEnabled
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP错误! 状态码: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // 移除加载状态
        removeLoadingMessage();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // 添加AI回复
        addMessage(data.answer, 'ai');
        
        // 显示各种类型的结果
        if (data.search_results && data.search_results.length > 0) {
            displaySearchResults(data.search_results, resultsContainer, '联网搜索结果');
        }
        
        if (data.vector_results && data.vector_results.length > 0) {
            displaySearchResults(data.vector_results, vectorResultsContainer, '向量检索结果');
        }
        
        if (data.database_results && data.database_results.length > 0) {
            displaySearchResults(data.database_results, databaseResultsContainer, '数据库检索结果');
        }
    })
    .catch(error => {
        // 移除加载状态
        removeLoadingMessage();
        
        console.error('请求失败:', error);
        addMessage(`处理问题时出错: ${error.message}`, 'ai');
    })
    .finally(() => {
        // 重新启用输入和发送
        sendBtn.disabled = false;
        userInput.disabled = false;
        userInput.focus();
    });
}

// 添加消息到聊天历史
function addMessage(content, sender, isTemp = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);
    if (isTemp) {
        messageDiv.id = 'temp-message';
    }
    
    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('avatar');
    avatarDiv.textContent = sender === 'user' ? '您' : 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('content');
    contentDiv.textContent = content;
    
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatHistory.appendChild(messageDiv);
    
    // 滚动到底部
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// 移除加载消息
function removeLoadingMessage() {
    const tempMessage = document.getElementById('temp-message');
    if (tempMessage) {
        tempMessage.remove();
    }
}

// 显示搜索结果
function displaySearchResults(results, container, titleText) {
    // 创建标题
    const title = document.createElement('h4');
    title.textContent = titleText;
    container.appendChild(title);
    
    // 显示每个结果
    results.forEach((result, index) => {
        const resultItem = document.createElement('div');
        resultItem.classList.add('result-item');
        
        // 创建结果标题
        const resultTitle = document.createElement('h5');
        resultTitle.textContent = result.title || `结果 ${index + 1}`;
        
        // 创建结果内容
        const content = document.createElement('p');
        content.textContent = result.content || result.snippet || '无详细内容';
        
        // 创建来源信息
        const source = document.createElement('div');
        source.classList.add('result-source');
        source.textContent = result.source || result.metadata?.source || '来源未知';
        
        resultItem.appendChild(resultTitle);
        resultItem.appendChild(content);
        resultItem.appendChild(source);
        container.appendChild(resultItem);
    });
}

// 发送日志到后端
function sendLog(action, details = '') {
    fetch(`${API_BASE_URL}/log`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: action,
            details: details,
            web_search: webSearchEnabled
        })
    })
    .then(response => {
        if (!response.ok) {
            console.error('日志发送失败');
        }
    })
    .catch(error => {
        console.error('日志发送错误:', error);
    });
}