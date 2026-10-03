/**
 * Job Analyzer — 1-Click LinkedIn Ingestion Bookmarklet
 * 
 * Instructions:
 * Drag this script or add a bookmark with the URL below into your browser bookmark bar.
 * While viewing any job on LinkedIn, click the bookmark to ingest and score it instantly!
 */

javascript:(function(){
  try {
    const titleEl = document.querySelector('h1, .job-details-jobs-unified-top-card__job-title, .topcard__title, .jobs-unified-top-card__job-title');
    const compEl = document.querySelector('.job-details-jobs-unified-top-card__company-name, .topcard__org-name-link, .jobs-unified-top-card__company-name');
    const descEl = document.querySelector('#job-details, .jobs-description__content, .description__text');
    const locEl = document.querySelector('.job-details-jobs-unified-top-card__bullet, .topcard__flavor--bullet, .jobs-unified-top-card__bullet');

    const title = titleEl ? titleEl.innerText.trim() : document.title;
    const company = compEl ? compEl.innerText.trim() : 'LinkedIn Company';
    const description = descEl ? descEl.innerText.trim() : document.body.innerText.substring(0, 2000);
    const location = locEl ? locEl.innerText.trim() : 'Dhaka, Bangladesh';

    const fullText = `${title}\n${company}\n${location}\n\n${description}`;

    fetch('http://127.0.0.1:8000/api/ingest/linkedin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: fullText,
        target_category_id: 8,
        user_skills: ['Python', 'React', 'DevOps', 'SQL'],
        user_experience: 3.5
      })
    })
    .then(res => res.json())
    .then(data => {
      const banner = document.createElement('div');
      banner.style.cssText = 'position:fixed;top:20px;right:20px;background:#10b981;color:#fff;padding:16px 24px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.5);z-index:999999;font-family:sans-serif;font-size:14px;display:flex;flex-direction:column;gap:6px;';
      banner.innerHTML = `<strong>Job Analyzer: Ingested!</strong>
        <span>Job: ${data.job ? data.job.title : title}</span>
        <span>Score: <strong>${data.score ? data.score.final_score : 'N/A'}</strong></span>
        <a href="http://127.0.0.1:8000" target="_blank" style="color:#fff;text-decoration:underline;font-weight:bold;margin-top:4px;">Open Dashboard &rarr;</a>`;
      document.body.appendChild(banner);
      setTimeout(() => banner.remove(), 7000);
    })
    .catch(err => {
      alert('Job Analyzer: Failed to send to local server. Make sure http://127.0.0.1:8000 is running.');
    });
  } catch(e) {
    alert('Job Analyzer bookmarklet error: ' + e.message);
  }
})();
