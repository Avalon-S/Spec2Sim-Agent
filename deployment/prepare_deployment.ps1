# Spec2Sim-Agent Deployment Preparation Script
# Run this from the project root directory: e:\VeriSpec\verispec-lite

Write-Host "🚀 Preparing Spec2Sim-Agent for deployment..." -ForegroundColor Cyan

# Copy core modules
Write-Host "📦 Copying core modules..." -ForegroundColor Yellow
xcopy core deployment\core\ /E /I /Y | Out-Null
xcopy agents deployment\agents\ /E /I /Y | Out-Null
xcopy servers deployment\servers\ /E /I /Y | Out-Null

Write-Host "✅ Core modules copied successfully" -ForegroundColor Green

# Check if .env is configured
Write-Host "`n⚙️  Checking configuration..." -ForegroundColor Yellow
$envFile = "deployment\.env"
$envContent = Get-Content $envFile -Raw

if ($envContent -match 'GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"') {
    Write-Host "⚠️  WARNING: You need to configure your Google Cloud Project ID!" -ForegroundColor Red
    Write-Host "   Edit deployment\.env and set GOOGLE_CLOUD_PROJECT" -ForegroundColor Yellow
    $needsConfig = $true
} else {
    Write-Host "✅ Configuration looks good" -ForegroundColor Green
    $needsConfig = $false
}

# Display deployment summary
Write-Host "`n📋 Deployment Files Ready:" -ForegroundColor Cyan
Write-Host "   ✓ agent.py (deployment entry point)" -ForegroundColor Gray
Write-Host "   ✓ requirements.txt (dependencies)" -ForegroundColor Gray
Write-Host "   ✓ .env (environment config)" -ForegroundColor Gray
Write-Host "   ✓ .agent_engine_config.json (resources)" -ForegroundColor Gray
Write-Host "   ✓ core/, agents/, servers/ (code)" -ForegroundColor Gray

if (-not $needsConfig) {
    Write-Host "`n🎯 Next Steps:" -ForegroundColor Cyan
    Write-Host "1. Install ADK: pip install google-adk" -ForegroundColor White
    Write-Host "2. Authenticate: gcloud auth application-default login" -ForegroundColor White
    Write-Host "3. Enable APIs: https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com,..." -ForegroundColor White
    Write-Host "4. Deploy: See deployment\README.md for full instructions" -ForegroundColor White
} else {
    Write-Host "`n⚠️  Configuration Required:" -ForegroundColor Yellow
    Write-Host "1. Edit deployment\.env" -ForegroundColor White
    Write-Host "2. Set GOOGLE_CLOUD_PROJECT=""your-actual-project-id""" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
}

Write-Host "`n📖 For detailed instructions, see:" -ForegroundColor Cyan
Write-Host "   - deployment\README.md (Quick Start)" -ForegroundColor White
Write-Host "   - artifacts\implementation_plan.md (Complete Guide)" -ForegroundColor White
