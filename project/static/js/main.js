// Global JS helper functions

function confirmDelete(message) {
    return confirm(message || "정말 삭제하시겠습니까?");
}

function toggleReplyForm(commentId) {
    const form = document.getElementById(`reply-form-${commentId}`);
    if (form.style.display === "none") {
        form.style.display = "block";
    } else {
        form.style.display = "none";
    }
}

async function toggleReaction(postId, reactionType) {
    try {
        const response = await fetch(`/posts/${postId}/react`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ type: reactionType })
        });
        
        if (response.ok) {
            // 반응 성공 시 페이지 새로고침하여 숫자를 정확히 반영 (요구사항)
            window.location.reload();
        } else {
            const data = await response.json();
            alert(data.error || '오류가 발생했습니다.');
        }
    } catch (err) {
        console.error(err);
        alert('서버와 통신 중 오류가 발생했습니다.');
    }
}
