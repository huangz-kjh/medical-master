const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const userImage = document.getElementById('user-image');
const inputWrapper = document.querySelector('.input-wrapper');
const sendButton = document.querySelector('.send-button');
const historyList = document.getElementById('history-list');
const searchInput = document.getElementById('search-input');
const newChatBtn = document.getElementById('new-chat-btn');

const BOT_AVATAR = "./static/img/Agent.png";

const USER_AVATAR = "./static/img/user.png";

let currentSessionId = null;
let isProcessing = false;

function debounce(func, timeout = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), timeout);
    };
}

function addMessage(role, content, timestamp = null) {
    // 移除欢迎消息或无消息提示（如果存在）
    const welcomeMessage = chatContainer.querySelector('.welcome-message');
    const noMessagesNotice = chatContainer.querySelector('.no-messages-notice');
    if (welcomeMessage) welcomeMessage.remove();
    if (noMessagesNotice) noMessagesNotice.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const timeStr = timestamp || new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    const avatar = role === 'bot' ? BOT_AVATAR : USER_AVATAR;

    msgDiv.innerHTML = `
        <div class="message-avatar">
            <img src="${avatar}" alt="${role === 'bot' ? '助手' : '用户'}">
        </div>
        <div class="message-bubble">
            <div class="message-content">${content}</div>
            <div class="message-meta">
                ${timeStr}
            </div>
        </div>
    `;

    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTo({top: chatContainer.scrollHeight, behavior: 'smooth'});
}

function showNoMessagesNotice() {
    chatContainer.innerHTML = `
        <div class="no-messages-notice">
            <div class="notice-icon">📝</div>
            <h2>此会话暂无消息</h2>
            <p>开始新的对话吧！</p>
        </div>
    `;
}

let abortController = null;

async function sendMessage() {
    if (isProcessing) return;
    
    if (abortController) {
        abortController.abort();
    }
    abortController = new AbortController();

    if (!validateMessage(true)) return;

    const message = userInput.value.trim();
    const imageFile = userImage.files[0];
    if (!message && !imageFile) return;

    try {
        isProcessing = true;
        updateUIState(true);

        // 如果是第一条消息，清除欢迎语
        const welcomeMessage = chatContainer.querySelector('.welcome-message');
        const isFirstMessage = !!welcomeMessage;
        
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        // 如果是第一条消息且没有当前会话ID，先创建新会话
        if (isFirstMessage || !currentSessionId) {
            try {
                const newChatResponse = await fetch('/chat/new');
                if (newChatResponse.ok) {
                    const html = await newChatResponse.text();
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    
                    // 获取新会话ID
                    const newSession = doc.querySelector('.current-session');
                    if (newSession) {
                        currentSessionId = newSession.dataset.sessionId;
                    }
                    
                    // 更新会话列表
                    const newHistoryList = doc.querySelector('.history-list');
                    if (newHistoryList) {
                        historyList.innerHTML = newHistoryList.innerHTML;
                        addDeleteSessionButton(); // 为新的会话列表添加删除按钮
                    }
                    
                    // 激活新会话
                    if (currentSessionId) {
                        const activeItems = historyList.querySelectorAll('.history-item.active');
                        activeItems.forEach(item => item.classList.remove('active'));
                        
                        const newActiveItem = historyList.querySelector(`[data-session-id="${currentSessionId}"]`);
                        if (newActiveItem) {
                            newActiveItem.classList.add('active');
                        }
                    }
                } else {
                    throw new Error('创建新会话失败');
                }
            } catch (error) {
                console.error('创建新会话失败:', error);
                addMessage('error', '创建新会话失败，请刷新页面重试');
                isProcessing = false;
                updateUIState(false);
                return;
            }
        }

        let userContent = message;
        if (imageFile) {
            const imageURL = URL.createObjectURL(imageFile);
            userContent += (message ? '<br>' : '') +
                `<img src="${imageURL}" alt="Uploaded Image" style="max-width:200px; max-height:200px;" />`;
        }
        addMessage('user', userContent);

        userInput.value = '';
        userImage.value = '';
        
        // 清除图片预览
        const previewContainer = document.getElementById('image-preview-container');
        if (previewContainer) {
            previewContainer.remove();
        }

        const formData = new FormData();
        formData.append("message", message);
        if (imageFile) {
            formData.append("image", imageFile);
        }
        if (currentSessionId) {
            formData.append("session_id", currentSessionId);
        }

        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot typing';
        typingDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        const response = await fetch('/chat', {
            method: 'POST',
            body: formData,
            signal: abortController.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        let decoder = new TextDecoder();
        let botResponse = '';
        let isDone = false;

        while (!isDone) {
            const {done, value} = await reader.read();
            if (done) {
                isDone = true;
                break;
            }

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        isDone = true;
                        break;
                    }
                    botResponse += data;
                }
            }
        }

        // 移除typing指示器
        const typingIndicators = document.querySelectorAll('.typing');
        typingIndicators.forEach(el => el.remove());

        if (botResponse.trim()) {
            addMessage('bot', botResponse);
        }

    } catch (error) {
        const errorMsg = error.name === 'AbortError' ? '请求已取消' : error.message;
        addMessage('error', `聊天失败: ${errorMsg}`);
    } finally {
        isProcessing = false;
        updateUIState(false);
        userInput.focus();
    }
}

function updateUIState(disabled) {
    const loadingDots = document.querySelector('.loading-dots');
    const buttonText = document.querySelector('.button-text');
    
    if (loadingDots) loadingDots.style.display = disabled ? 'inline' : 'none';
    if (buttonText) buttonText.style.display = disabled ? 'none' : 'inline';
    
    sendButton.disabled = disabled;
    userInput.disabled = disabled;
    userImage.disabled = disabled;
    newChatBtn.disabled = disabled;
}

async function refreshSessionList() {
    try {
        const response = await fetch('/chat');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const html = await response.text();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        const newHistoryList = tempDiv.querySelector('.history-list');
        if (newHistoryList) {
            historyList.innerHTML = newHistoryList.innerHTML;
            addDeleteSessionButton(); // 为新的会话列表添加删除按钮

            if (currentSessionId) {
                const activeItem = historyList.querySelector(`[data-session-id="${currentSessionId}"]`);
                if (activeItem) {
                    activeItem.classList.add('active');
                }
            }
        }
    } catch (error) {
        console.error('刷新会话列表失败:', error);
        addMessage('error', '刷新会话列表失败，请刷新页面重试');
    }
}

async function loadChatMessages(sessionId) {
    try {
        const response = await fetch(`/chat/${sessionId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const messages = await response.json();
        
        // 清除所有现有内容
        chatContainer.innerHTML = '';
        
        if (messages.length === 0) {
            showNoMessagesNotice();
            return;
        }

        messages.forEach(message => {
            addMessage(message.role, message.content, message.created_at);
        });

        chatContainer.scrollTo({top: chatContainer.scrollHeight, behavior: 'smooth'});
    } catch (error) {
        console.error('加载聊天消息失败:', error);
        addMessage('error', `加载消息失败: ${error.message}`);
    }
}

function validateMessage(showTip = false) {
    const hasContent = userInput.value.trim() || userImage.files[0];
    if (!hasContent) {
        userInput.setCustomValidity(showTip ? '请输入文字或上传图片' : '');
        if (showTip) userInput.reportValidity();
        return false;
    }
    userInput.setCustomValidity('');
    return true;
}

// 事件监听器
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

userInput.addEventListener('input', debounce(() => {
    userInput.setCustomValidity('');
    validateMessage(false);
}));

// 侧边栏切换功能
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.querySelector('.sidebar');
const mainContent = document.querySelector('.main-content');

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('hidden');
        sidebarToggle.classList.toggle('active');
        mainContent.classList.toggle('full-width');
        inputWrapper.classList.toggle('full-width');
    });
}

function clearChatContainer() {
    chatContainer.innerHTML = '';
    
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">👋</div>
            <h1>欢迎使用智能影像平台</h1>
            <p>我是您的智能聊天助手，请问有什么可以帮助您的吗？</p>
        </div>
    `;
}

newChatBtn.addEventListener('click', async () => {
    if (isProcessing) return;
    
    try {
        isProcessing = true;
        updateUIState(true);
        
        const response = await fetch('/chat/new');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        const newSession = doc.querySelector('.current-session');
        if (newSession) {
            currentSessionId = newSession.dataset.sessionId;
        }

        clearChatContainer();

        const newHistoryList = doc.querySelector('.history-list');
        if (newHistoryList) {
            historyList.innerHTML = newHistoryList.innerHTML;
            addDeleteSessionButton(); // 为新的会话列表添加删除按钮
        }

        const activeItems = historyList.querySelectorAll('.history-item.active');
        activeItems.forEach(item => item.classList.remove('active'));

        if (currentSessionId) {
            const newActiveItem = historyList.querySelector(`[data-session-id="${currentSessionId}"]`);
            if (newActiveItem) {
                newActiveItem.classList.add('active');
            }
        }
    } catch (error) {
        console.error('创建新会话失败:', error);
        addMessage('error', '创建新会话失败，请刷新页面重试');
    } finally {
        isProcessing = false;
        updateUIState(false);
    }
});

historyList.addEventListener('click', async (event) => {
    if (isProcessing) return;
    
    const historyItem = event.target.closest('.history-item');
    if (historyItem) {
        const sessionId = historyItem.dataset.sessionId;

        try {
            isProcessing = true;
            updateUIState(true);
            
            currentSessionId = sessionId;

            const activeItems = historyList.querySelectorAll('.history-item.active');
            activeItems.forEach(item => item.classList.remove('active'));
            historyItem.classList.add('active');

            await loadChatMessages(sessionId);
        } catch (error) {
            console.error('切换会话失败:', error);
            addMessage('error', '切换会话失败，请重试');
        } finally {
            isProcessing = false;
            updateUIState(false);
        }
    }
});

// 修改删除会话的功能
function addDeleteSessionButton() {
    const historyItems = document.querySelectorAll('.history-item');
    historyItems.forEach(item => {
        if (!item.querySelector('.delete-session')) {
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-session';
            deleteBtn.innerHTML = '🗑️';
            deleteBtn.title = '删除会话';
            
            deleteBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const sessionId = item.dataset.sessionId;
                if (confirm('确定要删除这个会话吗？')) {
                    try {
                        const response = await fetch(`/chat/session/${sessionId}`, {
                            method: 'DELETE'
                        });

                        if (response.ok) {
                            // 如果删除的是当前会话，创建新会话
                            if (currentSessionId === sessionId) {
                                // 创建新会话
                                const newChatResponse = await fetch('/chat/new');
                                if (newChatResponse.ok) {
                                    const html = await newChatResponse.text();
                                    const parser = new DOMParser();
                                    const doc = parser.parseFromString(html, 'text/html');
                                    
                                    // 获取新会话ID
                                    const newSession = doc.querySelector('.current-session');
                                    if (newSession) {
                                        currentSessionId = newSession.dataset.sessionId;
                                    }
                                    
                                    // 更新会话列表
                                    const newHistoryList = doc.querySelector('.history-list');
                                    if (newHistoryList) {
                                        historyList.innerHTML = newHistoryList.innerHTML;
                                        addDeleteSessionButton();
                                    }
                                    
                                    // 显示欢迎消息
                                    clearChatContainer();
                                    
                                    // 激活新会话
                                    if (currentSessionId) {
                                        const newActiveItem = historyList.querySelector(`[data-session-id="${currentSessionId}"]`);
                                        if (newActiveItem) {
                                            newActiveItem.classList.add('active');
                                        }
                                    }
                                } else {
                                    throw new Error('创建新会话失败');
                                }
                            } else {
                                // 如果删除的不是当前会话，只需从列表中移除
                                item.remove();
                            }
                        } else {
                            throw new Error('删除会话失败');
                        }
                    } catch (error) {
                        console.error('删除会话失败:', error);
                        addMessage('error', '删除会话失败，请重试');
                    }
                }
            });

            item.appendChild(deleteBtn);
        }
    });
}

function showWelcomeMessage() {
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">👋</div>
            <h1>欢迎使用智能影像平台</h1>
            <p>我是您的智能聊天助手，请问有什么可以帮助您的吗？</p>
        </div>
    `;
}

// 显示快捷按钮
function showQuickActions() {
    const quickActions = document.getElementById('quickActions');
    if (quickActions) {
        quickActions.style.display = 'flex';
        setTimeout(() => {
            quickActions.style.opacity = '1';
            quickActions.style.transform = 'translateX(-50%) translateY(0)';
        }, 300);
    }
}

// 在初始化和刷新会话列表后添加删除按钮
document.addEventListener('DOMContentLoaded', function() {
    const currentSession = document.querySelector('.current-session');
    if (currentSession) {
        currentSessionId = currentSession.dataset.sessionId;
    } else {
        currentSessionId = null; // 确保没有会话时设为null
    }
    
    // 初始化UI状态
    updateUIState(false);
    
    // 添加删除按钮到会话列表
    addDeleteSessionButton();
    
    // 显示快捷按钮
    showQuickActions();
    
    // 默认隐藏侧边栏
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const inputWrapper = document.querySelector('.input-wrapper');
    
    if (sidebar && mainContent && sidebarToggle && inputWrapper) {
        sidebar.classList.add('hidden');
        mainContent.classList.add('full-width');
        inputWrapper.classList.add('full-width');
        sidebarToggle.classList.add('active');
    }
    
    // 绑定所有快捷操作按钮点击事件
    document.querySelectorAll('.quick-action-btn').forEach(btn => {
        // 跳过医学助手按钮，避免重复绑定
        if (btn.id === 'reportGenerationBtn') return;
        btn.addEventListener('click', async function() {
            const action = this.dataset.action;
            if (!action) return;
            
            if (isProcessing) return;
            
            try {
                isProcessing = true;
                updateUIState(true);
                
                // 如果没有当前会话，创建一个新会话
                if (!currentSessionId) {
                    const newChatResponse = await fetch('/chat/new');
                    if (newChatResponse.ok) {
                        const html = await newChatResponse.text();
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        
                        // 获取新会话ID
                        const newSession = doc.querySelector('.current-session');
                        if (newSession) {
                            currentSessionId = newSession.dataset.sessionId;
                        }
                        
                        // 更新会话列表
                        const newHistoryList = doc.querySelector('.history-list');
                        if (newHistoryList) {
                            historyList.innerHTML = newHistoryList.innerHTML;
                            addDeleteSessionButton();
                        }
                        
                        // 激活新会话
                        if (currentSessionId) {
                            const activeItems = historyList.querySelectorAll('.history-item.active');
                            activeItems.forEach(item => item.classList.remove('active'));
                            
                            const newActiveItem = historyList.querySelector(`[data-session-id="${currentSessionId}"]`);
                            if (newActiveItem) {
                                newActiveItem.classList.add('active');
                            }
                        }
                    } else {
                        throw new Error('创建新会话失败');
                    }
                }
                
                // 移除欢迎消息
                const welcomeMessage = chatContainer.querySelector('.welcome-message');
                if (welcomeMessage) {
                    welcomeMessage.remove();
                }
                
                // 调用快速操作API
                const response = await fetch(`/api/chat/quick-action/${action}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                // 添加系统消息
                addMessage('bot', data.message || '请上传对应图片，我将帮您进行初步分析。');
                
            } catch (error) {
                console.error(`快捷操作 ${action} 执行失败:`, error);
                addMessage('error', `操作失败: ${error.message}`);
            } finally {
                isProcessing = false;
                updateUIState(false);
                userInput.focus();
            }
        });
    });
});

// 文件选择预览功能
userImage.addEventListener('change', function() {
    const imageFile = this.files[0];
    if (imageFile) {
        // 创建预览容器
        let previewContainer = document.getElementById('image-preview-container');
        
        // 如果预览容器不存在，则创建一个
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.id = 'image-preview-container';
            previewContainer.className = 'image-preview-container';
            inputWrapper.insertBefore(previewContainer, inputWrapper.querySelector('.input-group'));
        } else {
            // 清空已有的预览
            previewContainer.innerHTML = '';
        }
        
        // 创建图片预览
        const imagePreview = document.createElement('div');
        imagePreview.className = 'image-preview';
        
        // 创建图片元素
        const img = document.createElement('img');
        img.src = URL.createObjectURL(imageFile);
        img.alt = '图片预览';
        
        // 创建删除按钮
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-image-btn';
        removeBtn.innerHTML = '×';
        removeBtn.onclick = function() {
            userImage.value = ''; // 清除文件输入
            previewContainer.remove(); // 移除预览容器
        };
        
        // 添加元素到预览容器
        imagePreview.appendChild(img);
        imagePreview.appendChild(removeBtn);
        previewContainer.appendChild(imagePreview);
    }
});

// 在文件末尾添加弹窗功能
function showRagChatModal() {
    // 检查是否已存在弹窗
    let modal = document.getElementById('ragChatModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'ragChatModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100vw';
        modal.style.height = '100vh';
        modal.style.background = 'rgba(0,0,0,0.35)';
        modal.style.zIndex = '99999';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.innerHTML = `
            <div id="ragChatModalContent" style="background:#fff;max-width:900px;width:90vw;max-height:90vh;overflow:auto;border-radius:10px;box-shadow:0 4px 24px rgba(0,0,0,0.18);position:relative;padding:32px 24px 24px 24px;">
                <button id="closeRagChatModal" style="position:absolute;top:10px;right:16px;font-size:22px;background:none;border:none;cursor:pointer;">×</button>
                <div id="ragChatModalBody">加载中...</div>
            </div>
        `;
        document.body.appendChild(modal);
        document.getElementById('closeRagChatModal').onclick = function() {
            modal.remove();
        };
    } else {
        modal.style.display = 'flex';
    }
    // 加载rag_chat内容
    fetch('/api/rag_chat_html').then(r=>r.text()).then(html=>{
        document.getElementById('ragChatModalBody').innerHTML = html;
    }).catch(()=>{
        document.getElementById('ragChatModalBody').innerHTML = '加载失败';
    });
}

// 绑定医学助手按钮点击事件
const reportGenerationBtn = document.getElementById('reportGenerationBtn');
if (reportGenerationBtn) {
    reportGenerationBtn.addEventListener('click', function(e) {
        e.preventDefault();
        // 只弹窗，不发送任何快捷消息，不触发任何addMessage
        showRagChatModal();
    });
}

// 禁止reportGenerationBtn按钮再被其他快捷操作绑定