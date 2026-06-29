document.addEventListener('DOMContentLoaded', () => {
    const messageList = document.getElementById('message-list');
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    
    // As the user is in a session, we can get their ID from a hidden element or a global JS variable if needed.
    // For now, we'll just rely on the backend to know who the user is.
    // A simple way to get user id on the client side if needed:
    // const currentUserId = '{{ session.user.id }}'; // This would require the script to be in the HTML.
    // Since it's external, we'll rely on CSS classes returned from the server or compare IDs.
    
    const renderMessages = (messages, currentUserId) => {
        messageList.innerHTML = ''; // Clear the list
        messages.forEach(msg => {
            const item = document.createElement('div');
            item.classList.add('message-item');

            // Correctly determine message alignment and author styling
            if (msg.is_admin_sender || msg.is_admin) {
                item.classList.add('other-user'); // Admin is always 'other' in user's view
            } else if (msg.author_id === currentUserId) {
                item.classList.add('current-user'); // User's own messages
            } else {
                item.classList.add('other-user'); // Fallback for other participants
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

    // We need the current user's ID to correctly align messages.
    // Let's fetch it along with the messages.
    // A better way would be to have a dedicated endpoint for user info.
    const fetchUserAndMessages = async () => {
        try {
            // This is a temporary solution to get user ID. Ideally, it should be available globally.
            // We will make a call to a new endpoint to get session info
            const sessionResponse = await fetch('/api/get_session');
            const sessionData = await sessionResponse.json();
            
            if (sessionData && sessionData.user) {
                const messagesResponse = await fetch('/api/get_messages');
                const messages = await messagesResponse.json();
                renderMessages(messages, sessionData.user.id);
            }
        } catch (error) {
            console.error('Error fetching messages:', error);
        }
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        const text = messageInput.value.trim();
        if (text) {
            try {
                const response = await fetch('/api/send_message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: text })
                });
                
                if(response.ok) {
                    messageInput.value = '';
                    fetchUserAndMessages(); // Refetch messages to show the new one
                } else {
                    const errorData = await response.json();
                    console.error('Failed to send message:', errorData.message);
                }

            } catch (error) {
                console.error('Error sending message:', error);
            }
        }
    };

    messageForm.addEventListener('submit', handleSendMessage);
    
    // Initial fetch
    fetchUserAndMessages();
    
    // Poll for new messages every 3 seconds
    setInterval(fetchUserAndMessages, 3000);
});

// We need a new endpoint to get session data, let's add it to app.py
// GET /api/get_session
