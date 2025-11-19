let currentDataset = null
let charts = {
  bar: null,
  line: null,
  pie: null,
  histogram: null
}
let predictionData = null

async function listDatasets(){
  const res = await fetch('/api/datasets')
  const ds = await res.json()
  const ul = document.getElementById('datasetList')
  ul.innerHTML = ''
  ds.forEach(d=>{
    const li = document.createElement('li')
    li.className = 'list-group-item d-flex justify-content-between align-items-center'
    li.innerHTML = `
      <div style="cursor: pointer;" onclick="selectDataset(${d.id})">
        <strong>${d.original_name}</strong><br/>
        <small>${d.rows} rows · ${d.cols} cols</small>
      </div>
      <button class='btn btn-sm btn-danger' onclick="deleteDataset(${d.id}, event)">
        <span style="font-size: 1rem;">🗑️</span>
      </button>
    `
    ul.appendChild(li)
  })
}

async function deleteDataset(id, event){
  event.stopPropagation()
  
  if(!confirm('Are you sure you want to delete this dataset?')) return
  
  const res = await fetch(`/api/dataset/${id}`, {method: 'DELETE'})
  const data = await res.json()
  
  if(data.error) {
    alert(`Error: ${data.error}`)
    return
  }
  
  // If deleted dataset was selected, clear current selection
  if(currentDataset === id) {
    currentDataset = null
    document.getElementById('xSelect').innerHTML = '<option value="">Select X column</option>'
    document.getElementById('ySelect').innerHTML = '<option value="">Select Y column (numeric)</option>'
    document.getElementById('previewTable').innerHTML = ''
    
    // Clear all charts
    Object.keys(charts).forEach(type => {
      if(charts[type]) {
        charts[type].destroy()
        charts[type] = null
      }
    })
  }
  
  await listDatasets()
  alert('Dataset deleted successfully')
}

async function selectDataset(id){
  currentDataset = id
  // load columns
  const res = await fetch(`/api/dataset/${id}/columns`)
  const cols = await res.json()
  const xSel = document.getElementById('xSelect')
  const ySel = document.getElementById('ySelect')
  xSel.innerHTML = '<option value="">Select X column</option>'
  ySel.innerHTML = '<option value="">Select Y column (numeric)</option>'
  cols.forEach(c=>{
    const opt = document.createElement('option')
    opt.value = c.name
    opt.textContent = c.name + (c.is_numeric? ' (numeric)':'')
    xSel.appendChild(opt)
    if(c.is_numeric) ySel.appendChild(opt.cloneNode(true))
  })
  // load preview
  const p = await fetch(`/api/dataset/${id}/preview`)
  const data = await p.json()
  renderPreview(data)
}

function renderPreview(data){
  const table = document.getElementById('previewTable')
  table.innerHTML = ''
  const cols = data.columns
  if(!cols || cols.length===0) return
  const thead = document.createElement('thead')
  thead.innerHTML = '<tr>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr>'
  table.appendChild(thead)
  const tbody = document.createElement('tbody')
  data.rows.slice(0,50).forEach(r=>{
    const tr = document.createElement('tr')
    cols.forEach(c=>{ const td = document.createElement('td'); td.textContent = r[c]; tr.appendChild(td) })
    tbody.appendChild(tr)
  })
  table.appendChild(tbody)
}

async function makeChart(){
  if(!currentDataset) return alert('Select a dataset first')
  const x = document.getElementById('xSelect').value
  const y = document.getElementById('ySelect').value
  const type = document.getElementById('chartType').value
  const payload = { x: x }
  
  // For histogram, only x is needed (and it must be numeric)
  if(type === 'histogram') {
    if(!x) return alert('Select a numeric column for histogram')
    payload.type = type
  } else {
    if(y) payload.y = y
    payload.type = type
  }
  
  const res = await fetch(`/api/dataset/${currentDataset}/chart`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
  const data = await res.json()
  if(data.error) return alert(data.error)
  renderChart(data)
}

async function generateAllCharts(){
  if(!currentDataset) return alert('Select a dataset first')
  const x = document.getElementById('xSelect').value
  const y = document.getElementById('ySelect').value
  
  if(!x) return alert('Select X column')
  if(!y) return alert('Select Y column for bar, line, and pie charts')
  
  // Generate all chart types
  const chartTypes = ['bar', 'line', 'pie', 'histogram']
  
  for(const type of chartTypes) {
    const payload = { x: x, type: type }
    
    // For histogram, we only need x (must be numeric)
    // For other charts, we need both x and y
    if(type !== 'histogram') {
      payload.y = y
    }
    
    try {
      const res = await fetch(`/api/dataset/${currentDataset}/chart`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
      const data = await res.json()
      
      if(data.error) {
        console.error(`Error generating ${type} chart:`, data.error)
        continue
      }
      
      renderSpecificChart(data, type)
    } catch(error) {
      console.error(`Failed to generate ${type} chart:`, error)
    }
  }
  
  // Show prediction controls after charts are generated
  document.getElementById('predictionControls').style.display = 'block'
  
  // Show analysis reports section
  document.getElementById('analysisReportsSection').style.display = 'block'
}

function renderChart(data){
  const ctx = document.getElementById('chartCanvas').getContext('2d')
  if(chart) chart.destroy()
  
  // Determine chart type
  let chartType = data.type === 'pie' ? 'pie' : (data.type === 'histogram' ? 'bar' : data.type)
  
  const cfg = {
    type: chartType,
    data: {
      labels: data.labels,
      datasets: [{ 
        label: data.type === 'histogram' ? 'Frequency' : 'Value', 
        data: data.values, 
        backgroundColor: data.type === 'histogram' ? 'rgba(54, 162, 235, 0.6)' : data.labels.map((_,i)=>`hsl(${i*40 % 360} 70% 50%)`),
        borderColor: data.type === 'histogram' ? 'rgba(54, 162, 235, 1)' : undefined,
        borderWidth: data.type === 'histogram' ? 1 : 0
      }]
    },
    options: { 
      responsive:true,
      scales: data.type === 'histogram' ? {
        x: { title: { display: true, text: 'Range' } },
        y: { title: { display: true, text: 'Frequency' }, beginAtZero: true }
      } : undefined
    }
  }
  chart = new Chart(ctx, cfg)
}

function renderSpecificChart(data, chartType){
  const canvasId = chartType === 'histogram' ? 'histogramChart' : `${chartType}Chart`
  const canvas = document.getElementById(canvasId)
  if(!canvas) return
  
  const ctx = canvas.getContext('2d')
  
  // Destroy existing chart if it exists
  if(charts[chartType]) {
    charts[chartType].destroy()
  }
  
  // Determine actual Chart.js type
  let actualChartType = data.type === 'pie' ? 'pie' : (data.type === 'histogram' ? 'bar' : data.type)
  
  const cfg = {
    type: actualChartType,
    data: {
      labels: data.labels,
      datasets: [{ 
        label: data.type === 'histogram' ? 'Frequency' : 'Value', 
        data: data.values, 
        backgroundColor: data.type === 'histogram' ? 'rgba(54, 162, 235, 0.6)' : data.labels.map((_,i)=>`hsl(${i*40 % 360} 70% 50%)`),
        borderColor: data.type === 'histogram' ? 'rgba(54, 162, 235, 1)' : undefined,
        borderWidth: data.type === 'histogram' ? 1 : 0
      }]
    },
    options: { 
      responsive:true,
      maintainAspectRatio: true,
      scales: data.type === 'histogram' ? {
        x: { title: { display: true, text: 'Range' } },
        y: { title: { display: true, text: 'Frequency' }, beginAtZero: true }
      } : (data.type !== 'pie' ? {
        y: { beginAtZero: true }
      } : undefined)
    }
  }
  
  charts[chartType] = new Chart(ctx, cfg)
}

// upload
const uploadForm = document.getElementById('uploadForm')
uploadForm.addEventListener('submit', async (e)=>{
  e.preventDefault()
  const fileInput = document.getElementById('fileInput')
  if(!fileInput.files.length) return alert('Choose a file')
  const fd = new FormData()
  fd.append('file', fileInput.files[0])
  const res = await fetch('/api/upload', {method:'POST', body: fd})
  const data = await res.json()
  if(data.error) return alert(data.error)
  await listDatasets()
  alert('Upload complete')
})

// Generate all charts button
document.getElementById('generateAllCharts').addEventListener('click', generateAllCharts)

// Prediction function
async function showPrediction(years) {
  if(!currentDataset) return alert('Select a dataset first')
  
  const x = document.getElementById('xSelect').value
  const y = document.getElementById('ySelect').value
  
  if(!x || !y) return alert('Select both X and Y columns for prediction')
  
  const payload = { x: x, y: y, years: years }
  
  try {
    const res = await fetch(`/api/dataset/${currentDataset}/predict`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    })
    
    const data = await res.json()
    
    if(data.error) {
      alert(`Prediction Error: ${data.error}`)
      return
    }
    
    // Store prediction data
    predictionData = data
    
    // Display prediction info
    displayPredictionInfo(data, years)
    
    // Add predictions to charts
    addPredictionsToCharts(data)
    
  } catch(error) {
    console.error('Prediction failed:', error)
    alert('Failed to generate prediction')
  }
}

function displayPredictionInfo(data, years) {
  const infoDiv = document.getElementById('predictionInfo')
  const resultsDiv = document.getElementById('predictionResults')
  
  const trend = data.model_info.trend
  const r2 = (data.model_info.r2_score * 100).toFixed(2)
  const trendEmoji = trend === 'increasing' ? '📈' : trend === 'decreasing' ? '📉' : '➡️'
  
  let html = `
    <div class="mb-2">
      <strong>${trendEmoji} Trend:</strong> ${trend.toUpperCase()} (R² Score: ${r2}%)
    </div>
    <div class="mb-2">
      <strong>📊 Forecast for next ${years} years:</strong>
    </div>
    <ul class="mb-0">
  `
  
  data.forecast.forEach(f => {
    html += `<li>Year ${f.year}: X=${f.x.toFixed(2)}, Y=${f.y.toFixed(2)}</li>`
  })
  
  html += '</ul>'
  
  infoDiv.innerHTML = html
  resultsDiv.style.display = 'block'
}

function addPredictionsToCharts(data) {
  // Add prediction to line chart
  if(charts.line) {
    const lineChart = charts.line
    const currentLabels = [...lineChart.data.labels]
    const currentData = [...lineChart.data.datasets[0].data]
    
    // Add forecast labels and data
    const forecastLabels = data.forecast.map(f => `Year +${f.year}`)
    const forecastData = data.forecast.map(f => f.y)
    
    // Update chart with both current and forecast data
    lineChart.data.labels = [...currentLabels, ...forecastLabels]
    lineChart.data.datasets[0].data = [...currentData, ...forecastData]
    
    // Add a second dataset for predictions (different style)
    if(lineChart.data.datasets.length === 1) {
      lineChart.data.datasets.push({
        label: 'Predicted',
        data: [...Array(currentData.length).fill(null), ...forecastData],
        borderColor: 'rgba(255, 99, 132, 1)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderDash: [5, 5],
        borderWidth: 2
      })
    } else {
      lineChart.data.datasets[1].data = [...Array(currentData.length).fill(null), ...forecastData]
    }
    
    lineChart.update()
  }
  
  // Add prediction to bar chart
  if(charts.bar) {
    const barChart = charts.bar
    const currentLabels = [...barChart.data.labels]
    const currentData = [...barChart.data.datasets[0].data]
    
    const forecastLabels = data.forecast.map(f => `Year +${f.year}`)
    const forecastData = data.forecast.map(f => f.y)
    
    barChart.data.labels = [...currentLabels, ...forecastLabels]
    barChart.data.datasets[0].data = [...currentData, ...forecastData]
    
    // Update colors to differentiate predictions
    const currentColors = currentLabels.map((_, i) => `hsl(${i*40 % 360} 70% 50%)`)
    const forecastColors = forecastLabels.map(() => 'rgba(255, 99, 132, 0.6)')
    barChart.data.datasets[0].backgroundColor = [...currentColors, ...forecastColors]
    
    barChart.update()
  }
}

// Analysis Report Function
async function generateAnalysisReport() {
  if(!currentDataset) return alert('Select a dataset first')
  
  const x = document.getElementById('xSelect').value
  const y = document.getElementById('ySelect').value
  
  if(!x) return alert('Select X column for analysis')
  
  const payload = { x: x, y: y }
  
  try {
    const res = await fetch(`/api/dataset/${currentDataset}/analyze`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    })
    
    const data = await res.json()
    
    if(data.error) {
      alert(`Analysis Error: ${data.error}`)
      return
    }
    
    displayAnalysisReports(data)
    
  } catch(error) {
    console.error('Analysis failed:', error)
    alert('Failed to generate analysis reports')
  }
}

function displayAnalysisReports(data) {
  const container = document.getElementById('reportsContainer')
  container.innerHTML = ''
  
  if(!data.reports || data.reports.length === 0) {
    container.innerHTML = '<p class="text-muted">No reports available</p>'
    return
  }
  
  data.reports.forEach(report => {
    const reportCard = createReportCard(report)
    container.appendChild(reportCard)
  })
}

function createReportCard(report) {
  const card = document.createElement('div')
  card.className = 'report-card mb-3'
  
  const analysis = report.analysis
  
  let html = `
    <div class="report-header" onclick="toggleReport(${report.serial})">
      <div class="d-flex align-items-center gap-3">
        <div class="report-serial">${report.serial}</div>
        <div>
          <h6 class="mb-0">${report.icon} ${report.chart_type}</h6>
          <small class="text-muted">${analysis.summary}</small>
        </div>
      </div>
      <span class="toggle-icon" id="toggle-${report.serial}">▼</span>
    </div>
    <div class="report-body" id="report-body-${report.serial}" style="display: none;">
  `
  
  // Statistics Section
  if(analysis.statistics) {
    html += '<div class="report-section"><h6 class="report-section-title">📊 Key Statistics</h6><div class="stats-grid">'
    
    for(const [key, value] of Object.entries(analysis.statistics)) {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
      const displayValue = typeof value === 'number' ? value.toFixed(2) : value
      html += `
        <div class="stat-item">
          <div class="stat-label">${label}</div>
          <div class="stat-value">${displayValue}</div>
        </div>
      `
    }
    
    html += '</div></div>'
  }
  
  // Trend Analysis (for line chart)
  if(analysis.trend_analysis) {
    const trend = analysis.trend_analysis
    html += `
      <div class="report-section">
        <h6 class="report-section-title">📈 Trend Analysis</h6>
        <div class="trend-box">
          <div class="trend-direction">${trend.emoji} ${trend.direction} Trend</div>
          <div class="trend-details">
            <span>Slope: ${trend.slope.toFixed(4)}</span> | 
            <span>Change Rate: ${trend.change_rate}</span>
          </div>
        </div>
      </div>
    `
  }
  
  // Top Performers (for bar chart)
  if(analysis.top_performers && analysis.top_performers.length > 0) {
    html += '<div class="report-section"><h6 class="report-section-title">🏆 Top Performers</h6><ul class="performers-list">'
    analysis.top_performers.forEach(item => {
      html += `<li><strong>#${item.rank} ${item.category}:</strong> ${item.value.toFixed(2)}</li>`
    })
    html += '</ul></div>'
  }
  
  // Bottom Performers (for bar chart)
  if(analysis.bottom_performers && analysis.bottom_performers.length > 0) {
    html += '<div class="report-section"><h6 class="report-section-title">⚠️ Bottom Performers</h6><ul class="performers-list">'
    analysis.bottom_performers.forEach(item => {
      html += `<li><strong>#${item.rank} ${item.category}:</strong> ${item.value.toFixed(2)}</li>`
    })
    html += '</ul></div>'
  }
  
  // Distribution (for pie chart)
  if(analysis.distribution && analysis.distribution.length > 0) {
    html += '<div class="report-section"><h6 class="report-section-title">🥧 Distribution Breakdown</h6><div class="distribution-list">'
    analysis.distribution.forEach(item => {
      const percentage = parseFloat(item.percentage)
      html += `
        <div class="distribution-item">
          <div class="d-flex justify-content-between mb-1">
            <span><strong>#${item.rank} ${item.category}</strong></span>
            <span class="badge bg-primary">${item.percentage}</span>
          </div>
          <div class="progress" style="height: 8px;">
            <div class="progress-bar" style="width: ${percentage}%"></div>
          </div>
        </div>
      `
    })
    html += '</div></div>'
  }
  
  // Quartiles (for histogram)
  if(analysis.quartiles) {
    html += `
      <div class="report-section">
        <h6 class="report-section-title">📏 Quartile Analysis</h6>
        <div class="quartile-box">
          <div class="quartile-item">Q1 (25%): <strong>${analysis.quartiles.q1.toFixed(2)}</strong></div>
          <div class="quartile-item">Q2 (50%): <strong>${analysis.quartiles.q2.toFixed(2)}</strong></div>
          <div class="quartile-item">Q3 (75%): <strong>${analysis.quartiles.q3.toFixed(2)}</strong></div>
        </div>
      </div>
    `
  }
  
  // Key Insights
  if(analysis.key_insights && analysis.key_insights.length > 0) {
    html += '<div class="report-section"><h6 class="report-section-title">💡 Key Insights</h6><ul class="insights-list">'
    analysis.key_insights.forEach(insight => {
      html += `<li>${insight}</li>`
    })
    html += '</ul></div>'
  }
  
  html += '</div>'
  
  card.innerHTML = html
  return card
}

function toggleReport(serial) {
  const body = document.getElementById(`report-body-${serial}`)
  const toggle = document.getElementById(`toggle-${serial}`)
  
  if(body.style.display === 'none') {
    body.style.display = 'block'
    toggle.textContent = '▲'
  } else {
    body.style.display = 'none'
    toggle.textContent = '▼'
  }
}

// initial
listDatasets()
