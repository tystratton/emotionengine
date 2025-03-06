const emotionColors = {
    'neutral': '#808080',
    'admiration': '#FFD700',
    'amusement': '#FF69B4',
    'anger': '#FF4136',
    'annoyance': '#FF851B',
    'approval': '#2ECC40',
    'caring': '#B10DC9',
    'confusion': '#7FDBFF',
    'curiosity': '#01FF70',
    'desire': '#F012BE',
    'disappointment': '#AAAAAA',
    'disapproval': '#FF4136',
    'disgust': '#85144b',
    'embarrassment': '#FFB6C1',
    'excitement': '#FFD700',
    'fear': '#800080',
    'gratitude': '#98FB98',
    'grief': '#4A4A4A',
    'joy': '#FDB347',
    'love': '#FF69B4',
    'optimism': '#40E0D0',
    'pride': '#DAA520',
    'realization': '#87CEEB',
    'relief': '#98FB98',
    'remorse': '#708090',
    'sadness': '#4682B4',
    'surprise': '#DDA0DD'
};

// Initialize date picker when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize date picker
    const datePicker = flatpickr("#datePicker", {
        defaultDate: "today",
        maxDate: "today",
        dateFormat: "Y-m-d"
    });

    // Initial chart creation
    createTimelineChart();

    // Update chart when button is clicked
    document.getElementById('updateChart').addEventListener('click', function() {
        const selectedDate = datePicker.selectedDates[0];
        if (selectedDate) {
            const formattedDate = selectedDate.toISOString().split('T')[0]; // Format as YYYY-MM-DD
            createTimelineChart(formattedDate);
        }
    });
});

async function fetchTimelineData(date) {
    try {
        const url = date ? `/emotions/timeline?date=${date}` : '/emotions/timeline';
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
        return null;
    }
}

async function createTimelineChart(date) {
    // Show loading message
    document.getElementById('timelineLoadingMessage').style.display = 'block';
    document.getElementById('timelineChart').style.display = 'none';
    
    // Show loading for top content
    document.querySelector('#topComment .content-loading').style.display = 'block';
    document.querySelector('#topComment .content-body').style.display = 'none';
    document.querySelector('#topComment .score').style.display = 'flex';
    document.querySelector('#topComment .emotion').style.display = 'inline-block';
    
    document.querySelector('#topPost .content-loading').style.display = 'block';
    document.querySelector('#topPost .content-body').style.display = 'none';
    document.querySelector('#topPost .score').style.display = 'none'; // Hide score since we don't use it
    
    // Show post ID if it exists
    const postIdEl = document.querySelector('#topPost .post-id');
    if (postIdEl) {
        postIdEl.style.display = 'flex';
    }
    
    const timelineData = await fetchTimelineData(date);
    if (!timelineData) {
        document.getElementById('timelineLoadingMessage').textContent = 'Failed to load data';
        return;
    }

    // Update dominant emotion card
    if (timelineData.dominant_emotion) {
        document.getElementById('dominantEmotion').innerHTML = `
            <h3>Dominant Emotion</h3>
            <p>${timelineData.dominant_emotion.emotion}</p>
        `;
    }
    
    // Update top comment
    if (timelineData.top_comment) {
        const topCommentEl = document.getElementById('topComment');
        topCommentEl.querySelector('.content-loading').style.display = 'none';
        topCommentEl.querySelector('.content-body').style.display = 'block';
        
        // Truncate comment if too long
        let commentText = timelineData.top_comment.body;
        if (commentText.length > 300) {
            commentText = commentText.substring(0, 300) + '...';
        }
        
        topCommentEl.querySelector('.content-text').textContent = commentText;
        topCommentEl.querySelector('.author').textContent = `u/${timelineData.top_comment.author}`;
        topCommentEl.querySelector('.score-value').textContent = timelineData.top_comment.score;
        topCommentEl.querySelector('.emotion').textContent = timelineData.top_comment.emotion;
        
        // Since we don't have link_id, we'll use the post_id from the top post if available
        if (timelineData.top_post && timelineData.top_post.id) {
            // Create link element if it doesn't exist
            if (!topCommentEl.querySelector('.comment-link')) {
                const commentLinkEl = document.createElement('a');
                commentLinkEl.className = 'comment-link';
                commentLinkEl.innerHTML = '<i class="fas fa-external-link-alt"></i> View on Reddit';
                commentLinkEl.target = '_blank';
                topCommentEl.querySelector('.content-meta').appendChild(commentLinkEl);
            }
            
            // Update link using the post URL or ID
            const commentLinkEl = topCommentEl.querySelector('.comment-link');
            if (timelineData.top_post.url && timelineData.top_post.url !== '#') {
                commentLinkEl.href = timelineData.top_post.url;
            } else {
                commentLinkEl.href = `https://reddit.com/r/2007scape/comments/${timelineData.top_post.id}`;
            }
            commentLinkEl.style.display = 'inline-block';
        } else if (topCommentEl.querySelector('.comment-link')) {
            topCommentEl.querySelector('.comment-link').style.display = 'none';
        }
        
        // Add emotion color
        const emotionColor = emotionColors[timelineData.top_comment.emotion.toLowerCase()] || '#CCCCCC';
        topCommentEl.querySelector('.emotion').style.color = emotionColor;
    } else {
        // Handle no comment data
        const topCommentEl = document.getElementById('topComment');
        topCommentEl.querySelector('.content-loading').style.display = 'none';
        topCommentEl.querySelector('.content-body').style.display = 'block';
        topCommentEl.querySelector('.content-text').textContent = 'No comments found for this date.';
        topCommentEl.querySelector('.author').textContent = '';
        topCommentEl.querySelector('.score').style.display = 'none';
        topCommentEl.querySelector('.emotion').style.display = 'none';
        
        // Hide comment link if it exists
        if (topCommentEl.querySelector('.comment-link')) {
            topCommentEl.querySelector('.comment-link').style.display = 'none';
        }
    }
    
    // Update top post
    if (timelineData.top_post) {
        const topPostEl = document.getElementById('topPost');
        topPostEl.querySelector('.content-loading').style.display = 'none';
        topPostEl.querySelector('.content-body').style.display = 'block';
        
        topPostEl.querySelector('.post-title').textContent = timelineData.top_post.title;
        
        // Make the entire post card clickable by updating the link
        if (timelineData.top_post.url && timelineData.top_post.url !== '#') {
            topPostEl.querySelector('.post-link').href = timelineData.top_post.url;
        } else {
            topPostEl.querySelector('.post-link').href = `https://reddit.com/r/2007scape/comments/${timelineData.top_post.id}`;
        }
        
        topPostEl.querySelector('.author').textContent = `u/${timelineData.top_post.author}`;
        
        // Since we don't have score, hide the score element and show post ID instead
        topPostEl.querySelector('.score').style.display = 'none';
        
        // Add post ID if not already present
        if (!topPostEl.querySelector('.post-id')) {
            const postIdEl = document.createElement('span');
            postIdEl.className = 'post-id';
            postIdEl.innerHTML = `<i class="fas fa-hashtag"></i> <span class="id-value"></span>`;
            topPostEl.querySelector('.content-meta').appendChild(postIdEl);
        }
        
        // Update post ID
        const postIdEl = topPostEl.querySelector('.post-id');
        if (postIdEl) {
            postIdEl.style.display = 'flex';
            topPostEl.querySelector('.id-value').textContent = timelineData.top_post.id;
        }
    } else {
        // Handle no post data
        const topPostEl = document.getElementById('topPost');
        topPostEl.querySelector('.content-loading').style.display = 'none';
        topPostEl.querySelector('.content-body').style.display = 'block';
        topPostEl.querySelector('.post-title').textContent = 'No posts found for this date.';
        topPostEl.querySelector('.post-link').href = '#';
        topPostEl.querySelector('.author').textContent = '';
        topPostEl.querySelector('.score').style.display = 'none';
        
        // Hide post ID if it exists
        const postIdEl = topPostEl.querySelector('.post-id');
        if (postIdEl) {
            postIdEl.style.display = 'none';
        }
    }

    document.getElementById('timelineLoadingMessage').style.display = 'none';
    document.getElementById('timelineChart').style.display = 'block';

    // Clear existing legend
    const legendContainer = document.getElementById('legendContainer');
    legendContainer.innerHTML = '';
    
    // Create custom legend
    timelineData.emotions.forEach((emotion, index) => {
        const item = document.createElement('div');
        item.className = 'legend-item';
        const color = emotionColors[emotion.name.toLowerCase()] || '#CCCCCC';
        item.innerHTML = `
            <span class="legend-color" style="background-color: ${color}"></span>
            <span class="legend-label">${emotion.name}</span>
        `;
        item.dataset.index = index;
        item.addEventListener('click', () => toggleDataset(index));
        legendContainer.appendChild(item);
    });

    const ctx = document.getElementById('timelineChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.chart) {
        window.chart.destroy();
    }
    
    window.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timelineData.timestamps,
            datasets: timelineData.emotions.map(emotion => ({
                label: emotion.name,
                data: emotion.values,
                borderColor: emotionColors[emotion.name.toLowerCase()] || '#CCCCCC',
                backgroundColor: `${emotionColors[emotion.name.toLowerCase()]}33` || '#CCCCCC33',
                fill: true,
                tension: 0.4,
                borderWidth: 2
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false // Hide default legend
                },
                title: {
                    display: true,
                    text: 'Comment Emotions Over Time',
                    color: '#FFFFFF',
                    font: { family: 'Rubik', size: 16, weight: 'bold' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { 
                        color: 'rgba(255, 255, 255, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#FFFFFF',
                        font: { family: 'Rubik' },
                        padding: 10
                    },
                    title: {
                        display: true,
                        text: 'Number of Comments',
                        color: '#FFFFFF',
                        font: { family: 'Rubik', size: 12 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        color: '#FFFFFF',
                        font: { family: 'Rubik' },
                        padding: 10,
                        callback: function(value, index) {
                            // Get the time portion
                            const timeStr = this.getLabelForValue(value).split(' ')[1];
                            if (!timeStr) return '';
                            
                            // Parse the hour and return just the hour
                            const hour = parseInt(timeStr.split(':')[0]);
                            return `${hour.toString().padStart(2, '0')}:00`;
                        },
                        maxRotation: 90,
                        minRotation: 90
                    },
                    title: {
                        display: true,
                        text: 'Time (Hours)',
                        color: '#FFFFFF',
                        font: { family: 'Rubik', size: 12 }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function toggleDataset(index) {
    const legendItem = document.querySelector(`.legend-item[data-index="${index}"]`);
    legendItem.classList.toggle('inactive');
    
    const ci = window.chart;
    const meta = ci.getDatasetMeta(index);
    meta.hidden = !meta.hidden;
    ci.update();
} 