/* 量子通信信息监测平台 - 前端交互 */

// Toast 通知
function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast ' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

// 触发爬取
async function triggerCrawl() {
    const btn = document.getElementById('btn-crawl');
    btn.disabled = true;
    btn.textContent = '爬取中...';

    try {
        const resp = await fetch('/api/crawl/trigger', { method: 'POST' });
        const data = await resp.json();
        showToast(data.message || '爬取任务已启动', 'success');

        // 轮询状态
        pollCrawlStatus();
    } catch (e) {
        showToast('启动爬取失败: ' + e.message, 'error');
        btn.disabled = false;
        btn.textContent = '立即爬取';
    }
}

// 轮询爬取状态
let pollTimer = null;
async function pollCrawlStatus() {
    const btn = document.getElementById('btn-crawl');
    let attempts = 0;
    const maxAttempts = 60; // 最多轮询 5 分钟

    if (pollTimer) clearInterval(pollTimer);

    pollTimer = setInterval(async () => {
        attempts++;
        try {
            const resp = await fetch('/api/crawl/status');
            const data = await resp.json();
            const log = data.latest_log;

            if (log && log.status !== 'running') {
                clearInterval(pollTimer);
                btn.disabled = false;
                btn.textContent = '立即爬取';
                showToast(`爬取完成：新增 ${log.new_articles} 条`, 'success');
                // 刷新页面更新数据
                setTimeout(() => location.reload(), 1500);
            } else if (attempts >= maxAttempts) {
                clearInterval(pollTimer);
                btn.disabled = false;
                btn.textContent = '立即爬取';
                showToast('爬取超时，请稍后刷新查看', 'warning');
            } else {
                btn.textContent = `爬取中 (${attempts * 5}s)...`;
            }
        } catch (e) {
            clearInterval(pollTimer);
            btn.disabled = false;
            btn.textContent = '立即爬取';
        }
    }, 5000);
}

// 生成报告
async function generateReport() {
    const start = document.getElementById('report-start').value;
    const end = document.getElementById('report-end').value;

    if (!start || !end) {
        showToast('请选择开始和结束日期', 'warning');
        return;
    }

    try {
        const resp = await fetch('/api/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start_date: start, end_date: end })
        });
        const data = await resp.json();

        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        showToast('报告已生成', 'success');
        window.open('/reports/' + data.filename, '_blank');
    } catch (e) {
        showToast('生成报告失败: ' + e.message, 'error');
    }
}

// 列出报告
async function listReports() {
    const resp = await fetch('/api/report/list');
    const data = await resp.json();

    if (data.reports.length === 0) {
        showToast('暂无已生成的报告', 'info');
        return;
    }

    // 打开最新报告
    window.open('/reports/' + data.reports[0].filename, '_blank');
}

// 设置默认日期（最近 7 天）
(function() {
    const today = new Date();
    const weekAgo = new Date(today);
    weekAgo.setDate(today.getDate() - 7);

    document.getElementById('report-start').value = weekAgo.toISOString().split('T')[0];
    document.getElementById('report-end').value = today.toISOString().split('T')[0];
})();
