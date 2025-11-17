let currentDataset = null
let charts = {
  bar: null,
  line: null,
  pie: null,
  histogram: null
}

async function listDatasets(){
  const res = await fetch('/api/datasets')
  const ds = await res.json()
  const ul = document.getElementById('datasetList')
  ul.innerHTML = ''
  ds.forEach(d=>{
    const li = document.createElement('li')
    li.className = 'list-group-item d-flex justify-content-between align-items-start'
    li.innerHTML = `<div><strong>${d.original_name}</strong><br/><small>${d.rows} rows · ${d.cols} cols</small></div><div><button class='btn btn-sm btn-outline-primary'>Open</button></div>`
    li.onclick = ()=>{ selectDataset(d.id) }
    ul.appendChild(li)
  })
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

// initial
listDatasets()
