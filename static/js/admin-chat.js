document.addEventListener('DOMContentLoaded', () => {
    const userList = document.querySelector('.chat-user-list');
    const messageList = document.getElementById('admin-message-list');
    const messageFormContainer = document.getElementById('admin-message-form-container');
    const messageForm = document.getElementById('admin-message-form');
    const messageInput = document.getElementById('admin-message-input');
    const placeholder = document.querySelector('.message-placeholder');

    let activeChatUserId = null;
    let chatInterval = null;

    // Render messages in the admin chat window
    const renderMessages = (messages, adminId) => {
        messageList.innerHTML = ''; // Clear the list
        if (messages.length === 0) {
            placeholder.textContent = 'Повідомлень ще немає.';
            placeholder.style.display = 'block';
            return;
        }
        
        placeholder.style.display = 'none';

        messages.forEach(msg => {
            const item = document.createElement('div');
            item.classList.add('message-item');

            // Align messages based on who sent them
            // This now checks for both legacy and current admin flags
            if (msg.is_admin_sender || msg.is_admin) {
                item.classList.add('current-user'); // Admin's own messages on the right
            } else {
                item.classList.add('other-user'); // User's messages on the left
            }
            
            const text = document.createElement('p');
            text.classList.add('message-text');
            text.textContent = msg.text;
            
            const meta = document.createElement('div');
            meta.classList.add('message-meta');
            meta.innerHTML = `<span>${msg.author_name}</span> - ${msg.timestamp}`;
            
            item.appendChild(text);
            item.appendChild(meta);
            messageList.appendChild(item);
        });
        messageList.scrollTop = messageList.scrollHeight; // Scroll to the bottom
    };

    const fetchAndRenderMessages = async (userId) => {
        if (!userId) return;
        try {
            const response = await fetch(`/api/get_messages?user_id=${userId}`);
            const messages = await response.json();
            renderMessages(messages);
        } catch (error) {
            console.error('Error fetching messages:', error);
        }
    };
    
    // Switch to a different user's chat
    const selectUser = (userElement) => {
        // Clear existing interval
        if (chatInterval) {
            clearInterval(chatInterval);
        }

        activeChatUserId = userElement.dataset.userId;

        // Update active class
        document.querySelectorAll('.chat-user-item').forEach(el => el.classList.remove('active'));
        userElement.classList.add('active');

        // Show form and fetch messages
        messageFormContainer.style.display = 'block';
        messageList.innerHTML = '<div class="message-placeholder">Завантаження...</div>';
        
        fetchAndRenderMessages(activeChatUserId);

        // Start new polling interval
        chatInterval = setInterval(() => fetchAndRenderMessages(activeChatUserId), 3000);
    };

    // Handle sending a message as an admin
    const handleSendMessage = async (e) => {
        e.preventDefault();
        const text = messageInput.value.trim();
        
        if (text && activeChatUserId) {
            try {
                const response = await fetch('/api/send_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: text,
                        recipient_user_id: activeChatUserId 
                    })
                });
                
                if (response.ok) {
                    messageInput.value = '';
                    fetchAndRenderMessages(activeChatUserId); // Refetch immediately
                } else {
                    const errorData = await response.json();
                    alert(`Failed to send message: ${errorData.message}`);
                }
            } catch (error) {
                console.error('Error sending message:', error);
            }
        }
    };

    // Event delegation for user selection
    if (userList) {
        userList.addEventListener('click', (e) => {
            const userItem = e.target.closest('.chat-user-item');
            if (userItem) {
                selectUser(userItem);
            }
        });
    }

    if (messageForm) {
        messageForm.addEventListener('submit', handleSendMessage);
    }
});
