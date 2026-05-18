# 수원대 LMS Sync — 배포용 .exe 빌드 스크립트
#
# 사용법:
#   cd backend
#   .\build-exe.ps1
#
# 동작:
#   1. 이전 build/ dist/ 정리
#   2. PyInstaller 로 .exe 빌드
#   3. 결과를 dist/release/ 로 정리 (개인 데이터 없는 깨끗한 상태)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host ""
Write-Host "=== 수원대 LMS Sync .exe 빌드 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 이전 빌드 정리
Write-Host "[1/4] 이전 빌드 산출물 정리..." -ForegroundColor Yellow
if (Test-Path "$root\build") { Remove-Item -Recurse -Force "$root\build" }
if (Test-Path "$root\dist")  { Remove-Item -Recurse -Force "$root\dist" }

# 2. PyInstaller 실행
Write-Host "[2/4] PyInstaller 빌드 중... (3~5분 소요)" -ForegroundColor Yellow
$python = "$root\app\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "ERROR: venv 가 없습니다. 먼저 가상환경 + pip install 을 끝내세요." -ForegroundColor Red
    exit 1
}
& $python -m PyInstaller "$root\suwon-lms-sync.spec" --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller 빌드 실패" -ForegroundColor Red
    exit 1
}

# 3. 배포 폴더 정리
Write-Host "[3/4] 배포 폴더 정리 (개인 데이터 제외)..." -ForegroundColor Yellow
$release = "$root\dist\suwon-lms-sync"
if (Test-Path $release) {
    # .env.example 만 포함, .env 는 제외
    $exampleSrc = "$root\app\.env.example"
    if (Test-Path $exampleSrc) {
        Copy-Item $exampleSrc "$release\.env.example" -Force
    }
    # 혹시 모를 개인 데이터 잔류분 제거
    @("lms_sync.db", "lms_sync.db-wal", "lms_sync.db-shm", ".env") | ForEach-Object {
        $p = "$release\$_"
        if (Test-Path $p) { Remove-Item $p -Force }
    }
    # downloads 폴더는 처음 실행 시 자동 생성되니 미리 만들 필요 없음
}

# 4. 결과 안내
Write-Host "[4/4] 완료." -ForegroundColor Green
Write-Host ""
Write-Host "결과 위치:" -ForegroundColor Cyan
Write-Host "  $release\suwon-lms-sync.exe"
Write-Host ""
Write-Host "배포 시 dist\suwon-lms-sync\ 폴더 전체를 zip 으로 묶어서 전달하세요." -ForegroundColor Cyan
Write-Host "사용자는 .exe 더블클릭으로 실행, 트레이 아이콘이 뜨면 정상." -ForegroundColor Cyan
Write-Host ""
