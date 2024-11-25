$ErrorActionPreference = "Stop"

$Version = (Get-Content $PSScriptRoot/../version.txt)
$Version = $Version.Trim()
$WorkPath = "$PSScriptRoot/../build"
$DistPath = "$PSScriptRoot/../dist"
$ReleasePath = "$PSScriptRoot/../release"
Write-Output $Version
New-Item -ItemType Directory -Force -Path $WorkPath
New-Item -ItemType Directory -Force -Path $DistPath
Get-ChildItem -Path $DistPath -Include * | Remove-Item -Recurse 
(Get-Content $PSScriptRoot/versionfile.yml.in).Replace('#VERSION#', $Version) | Set-Content $WorkPath/versionfile.yml
$Name = "domainmapper"
create-version-file $WorkPath/versionfile.yml --outfile $WorkPath/win32_versionfile.txt

pyinstaller --onefile `
            --console `
            --noconfirm `
            --clean `
            --specpath=$WorkPath `
            --distpath=$DistPath `
            --workpath=$WorkPath `
            --name=$Name `
            --icon=$PSScriptRoot/logo.ico `
            --version-file=$WorkPath/win32_versionfile.txt `
            --optimize=1 `
            $PSScriptRoot/../main.py

Copy-Item -Path $PSScriptRoot/../config.ini -Destination $DistPath/config.ini
Copy-Item -Path $PSScriptRoot/../dnsdb -Destination $DistPath/dnsdb
Copy-Item -Path $PSScriptRoot/../custom-dns-list.txt -Destination $DistPath/custom-dns-list.txt
Copy-Item -Path $PSScriptRoot/../platformdb -Destination $DistPath/platformdb
Copy-Item -Path $PSScriptRoot/../platforms -Destination $DistPath -Recurse

New-Item -ItemType Directory -Force -Path $ReleasePath
$ReleaseArchive = "$ReleasePath/$Name-v$Version.zip"
Remove-Item $ReleaseArchive -Force
Compress-Archive -Path $DistPath/* -DestinationPath $ReleaseArchive