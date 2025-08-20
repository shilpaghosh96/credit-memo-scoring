document.getElementById('scorecard-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const submitBtn = document.getElementById('submit-btn');
    const loader = document.getElementById('loader');
    const resultsSection = document.getElementById('results-section');
    const errorSection = document.getElementById('error-section');

    // Hide previous results and show loader
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    loader.classList.remove('hidden');
    submitBtn.disabled = true;

    try {
        const response = await fetch('/score/', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'An unknown error occurred.');
        }

        const results = await response.json();
        displayResults(results);

    } catch (error) {
        errorSection.textContent = `Error: ${error.message}`;
        errorSection.classList.remove('hidden');
    } finally {
        // Hide loader and re-enable button
        loader.classList.add('hidden');
        submitBtn.disabled = false;
    }
});

function displayResults(results) {
    const results3mContainer = document.getElementById('results-3m');
    const results6mContainer = document.getElementById('results-6m');
    const resultsSection = document.getElementById('results-section');

    results3mContainer.innerHTML = createResultCardHTML('3 Months', results['3m']);
    results6mContainer.innerHTML = createResultCardHTML('6 Months', results['6m']);

    resultsSection.classList.remove('hidden');
}

function createResultCardHTML(window, data) {
    if (data.error) {
        return `<h3>${window}</h3><p class="error">Error: ${data.error}</p><p>${JSON.stringify(data.details)}</p>`;
    }

    const { scorecard, pdf_download_url } = data;
    const grade = scorecard.grade || 'N/A';

    return `
        <h3>${window}</h3>
        <div class="grade grade-${grade}">${grade}</div>
        <p><strong>Score:</strong> ${scorecard.score.toFixed(1)}</p>
        <p><strong>Eligible Capital:</strong> $${scorecard.eligible_capital.toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
        <p><strong>Annual ECL:</strong> $${scorecard.expected_loss_annualized.toLocaleString('en-US', { maximumFractionDigits: 0 })}</p>
        <p><strong>Reasons:</strong> ${scorecard.reason_codes.join(', ')}</p>
        <a href="${pdf_download_url}" class="download-btn" target="_blank">Download PDF</a>
    `;
}
