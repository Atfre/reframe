param(
    [string]$SourceArchive = '',
    [string]$Make = 'build/msys-make/usr/bin/make.exe',
    [string]$Bash = 'C:\Program Files\Git\bin\bash.exe',
    [switch]$Reconfigure
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$dependencies = Get-Content (Join-Path $PSScriptRoot 'dependencies.json') -Raw | ConvertFrom-Json
$dependency = $dependencies.ffmpeg_source
if (-not $SourceArchive) { $SourceArchive = Join-Path 'build' $dependency.filename }
$archive = (Resolve-Path -LiteralPath $SourceArchive).Path
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $dependency.sha256) {
    throw 'Unexpected FFmpeg source archive; use the pinned release in tools/dependencies.json.'
}
$makePath = (Resolve-Path -LiteralPath $Make).Path
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Install Visual Studio C++ Build Tools (development only).' }
# Import the developer environment; never copy compiler tools to the runtime.
Import-Module (Join-Path $vs 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll')
$env:PATH = (Split-Path $vswhere -Parent) + ';' + $env:PATH
Enter-VsDevShell -VsInstallPath $vs -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null
$env:PATH += ';' + (Join-Path (Split-Path (Split-Path $Bash -Parent) -Parent) 'usr\bin')
$work = Join-Path $repo 'build'
$dav1d = Join-Path $work ('dav1d-' + $dependencies.dav1d_source.version)
$meson = Join-Path $work ('meson-' + $dependencies.meson_development_only.version + '/meson.py')
$davBuild = Join-Path $work 'dav1d-build'
$davPrefix = Join-Path $work 'dav1d-install'
$pkgconf = Join-Path $work 'msys-pkgconf/usr/bin/pkgconf.exe'
foreach ($key in 'dav1d_source', 'meson_development_only', 'pkgconf_development_only') {
    $inputDependency = $dependencies.$key
    $inputArchive = Join-Path $work $inputDependency.filename
    if (-not (Test-Path -LiteralPath $inputArchive) -or
        (Get-FileHash -LiteralPath $inputArchive -Algorithm SHA256).Hash -ne $inputDependency.sha256) {
        throw "Missing or changed $key. Run tools/prepare_build.py."
    }
}
$ninja = Join-Path $vs 'Common7/IDE/CommonExtensions/Microsoft/CMake/Ninja'
if (-not (Test-Path (Join-Path $ninja 'ninja.exe'))) { throw 'Install the Visual Studio C++ CMake tools (development only).' }
$env:PATH = $ninja + ';' + $env:PATH
if (-not (Test-Path (Join-Path $davBuild 'build.ninja'))) {
    & python $meson setup $davBuild $dav1d --prefix $davPrefix --libdir lib --buildtype release --default-library static '-Db_vscrt=mt' '-Denable_asm=false' '-Denable_tools=false' '-Denable_examples=false' '-Denable_tests=false'
    if ($LASTEXITCODE) { throw 'dav1d configure failed.' }
}
& python $meson compile -C $davBuild
if ($LASTEXITCODE) { throw 'dav1d compilation failed.' }
& python $meson install -C $davBuild --no-rebuild
if ($LASTEXITCODE) { throw 'dav1d install into build/ failed.' }
# FFmpeg's MSVC flag adapter maps -ldav1d to dav1d.lib.
Copy-Item -LiteralPath (Join-Path $davPrefix 'lib/libdav1d.a') -Destination (Join-Path $davPrefix 'lib/dav1d.lib') -Force
$source = Join-Path $work ('ffmpeg-' + $dependency.version)
if (-not (Test-Path -LiteralPath $source)) {
    & python -c "import sys,tarfile; tarfile.open(sys.argv[1]).extractall(sys.argv[2], filter='data')" $archive $work
    if ($LASTEXITCODE) { throw 'Could not extract FFmpeg.' }
}
$build = Join-Path $work ('ffmpeg-' + $dependency.version + '-build')
New-Item -ItemType Directory -Force -Path $build | Out-Null
# FFmpeg uses src/ for compile paths when this local junction exists.
$sourceLink = Join-Path $build 'src'
if (Test-Path -LiteralPath $sourceLink) {
    $link = Get-Item -LiteralPath $sourceLink -Force
    if ($link.LinkType -notin @('Junction', 'SymbolicLink') -or
        [IO.Path]::GetFullPath([IO.Path]::Combine($build, $link.Target)) -ne [IO.Path]::GetFullPath($source)) {
        throw 'Unexpected build/src path. Use a fresh build directory.'
    }
} else {
    New-Item -ItemType Junction -Path $sourceLink -Target $source | Out-Null
}
$configure = (Join-Path $PSScriptRoot 'ffmpeg-configure.sh').Replace('\', '/')
$sourcePosix = $source.Replace('\', '/')
$previousCompilerOptions = $env:_CL_
# Included headers can otherwise retain absolute __FILE__ paths even through src/.
$env:_CL_ = ($previousCompilerOptions + ' /d1trimfile:"' + $build + '"').Trim()
Push-Location $build
try {
    if ($Reconfigure -or -not (Test-Path 'ffbuild/config.mak')) {
        if (Test-Path 'ffbuild/config.mak') {
            & $makePath 'SHELL=/usr/bin/sh' clean
            if ($LASTEXITCODE) { throw 'Could not clean the previous FFmpeg configuration.' }
        }
        & $Bash $configure $sourcePosix $davPrefix.Replace('\', '/') $pkgconf.Replace('\', '/')
        if ($LASTEXITCODE) { throw 'FFmpeg configure failed. See ffbuild/config.log.' }
    }
    & $makePath -j4 'SHELL=/usr/bin/sh' ffmpeg.exe ffprobe.exe
    if ($LASTEXITCODE) { throw 'FFmpeg compilation failed.' }
} finally {
    Pop-Location
    $env:_CL_ = $previousCompilerOptions
}
Write-Host "Built runtime in $build"
