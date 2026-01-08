package main

import (
	"archive/zip"
	"embed"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync/atomic"

	// "syscall"
	"time"
)

// ======================= CONFIG =======================

const (
	AppName = "q2sfx"
)

type CliOptions struct {
	Path           string
	ShortcutName   string
	CreateShortcut bool
	Console        bool
}

var defaultConsole = "false"

// overwritePaths будет вычисляться динамически из имени payload
var overwritePaths []string

// ======================= EMBED ========================

//go:embed payload/*.zip
var payloadFS embed.FS

// ======================= UTILS ========================

func abort(msg string) {
	fmt.Println("ERROR:", msg)
	os.Exit(1)
}

func exists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func shouldOverwrite(zipPath string) bool {
	if zipPath == "" {
		return false
	}

	// Normalize all separators to '/'
	zipPath = strings.ReplaceAll(zipPath, "\\", "/")

	// Remove leading "./"
	zipPath = strings.TrimPrefix(zipPath, "./")

	// Split into components
	parts := strings.Split(zipPath, "/")

	// Expect: appBase/...
	if len(parts) < 2 {
		return false
	}

	top := parts[1] // assets, _internal, appBase(.exe)

	for _, p := range overwritePaths {
		if top == p || strings.HasPrefix(top, p+".") {
			return true
		}
	}

	return false
}

var progressCurrent int64
var progressTotal int64
var progressDone int32

var spinnerFrames = []rune{'⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'}
var spinnerIndex int32

func startProgressRenderer() {
	ticker := time.NewTicker(100 * time.Millisecond)
	go func() {
		defer ticker.Stop()
		for range ticker.C {
			if atomic.LoadInt32(&progressDone) == 1 {
				return
			}
			renderProgress()
		}
	}()
}

func renderProgress() {
	total := atomic.LoadInt64(&progressTotal)
	current := atomic.LoadInt64(&progressCurrent)
	if total == 0 {
		return
	}

	percent := float64(current) / float64(total)
	barWidth := 50
	filled := int(percent * float64(barWidth))
	if filled > barWidth {
		filled = barWidth
	}

	spin := spinnerFrames[atomic.AddInt32(&spinnerIndex, 1)%int32(len(spinnerFrames))]
	bar := string(repeat('=', filled)) + string(repeat(' ', barWidth-filled))

	fmt.Printf("\r%c [%s] %3.0f%%", spin, bar, percent*100)
}

func repeat(char rune, count int) []rune {
	s := make([]rune, count)
	for i := range s {
		s[i] = char
	}
	return s
}

func stripFirstSegment(p string) string {
	// нормализуем разделители под текущую ОС
	clean := filepath.Clean(p)

	// сохраняем информацию об абсолютном пути / диске
	vol := filepath.VolumeName(clean)
	rest := strings.TrimPrefix(clean, vol)

	// убираем ведущий разделитель
	rest = strings.TrimPrefix(rest, string(filepath.Separator))

	parts := strings.SplitN(rest, string(filepath.Separator), 2)
	if len(parts) == 2 {
		return filepath.Join(vol, parts[1])
	}

	return p
}

func ParseCli() *CliOptions {
	defaultConsoleBool := defaultConsole == "true"

	noShortcut := flag.Bool(
		"no-shortcut",
		false,
		"do not create a shortcut",
	)

	shortcutName := flag.String(
		"shortcut-name",
		"",
		"name of the shortcut (default: application name)",
	)

	console := flag.Bool(
		"console",
		defaultConsoleBool,
		"force console mode for payload application",
	)

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, `Usage: %s [options] [path]

Options:
`, os.Args[0])
		flag.PrintDefaults()
		fmt.Fprintf(os.Stderr, `
[path] (optional)
    Installation directory (default: application name).
`)
	}

	flag.Parse()

	opts := &CliOptions{
		ShortcutName:   *shortcutName,
		CreateShortcut: !*noShortcut,
		Console:        *console,
	}

	// optional positional path
	if args := flag.Args(); len(args) > 0 {
		opts.Path = args[0]
	}

	return opts
}

// ======================= INSTALL ======================

var opts = ParseCli()

func extractPayload(target string) (string, error) {
	// найти zip в payload
	entries, err := payloadFS.ReadDir("payload")
	if err != nil {
		return "", err
	}

	var zipName string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".zip") {
			zipName = e.Name()
			break
		}
	}
	if zipName == "" {
		return "", fmt.Errorf("no zip payload found in payload/")
	}

	// base project name = zip name w/o .zip
	appBase := strings.TrimSuffix(zipName, ".zip")

	overwritePaths = []string{"_internal", "assets", appBase}

	if opts.Path == "" {
		opts.Path = appBase
	}
	fmt.Println("Installing SFX:", appBase, "...")
	absPath, _ := filepath.Abs(opts.Path)
	fmt.Println("Target directory    :", absPath)

	zipPath := "payload/" + zipName

	r, err := payloadFS.Open(zipPath)
	if err != nil {
		return "", err
	}
	defer r.Close()

	tmp, err := os.CreateTemp("", "q2sfx-*.zip")
	if err != nil {
		return "", err
	}
	defer os.Remove(tmp.Name())

	if _, err := io.Copy(tmp, r); err != nil {
		return "", err
	}
	tmp.Close()

	z, err := zip.OpenReader(tmp.Name())
	if err != nil {
		return "", err
	}
	defer z.Close()

	var totalSize int64
	for _, f := range z.File {
		totalSize += int64(f.UncompressedSize64)
	}

	atomic.StoreInt64(&progressTotal, totalSize)
	startProgressRenderer()
	var rollbackFiles []string
	var rollbackDirs []string
	var firstInstall []string

	var copied int64
	for _, f := range z.File {
		dest := filepath.Join(opts.Path, stripFirstSegment(f.Name))
		top := getTopSegment(f.Name) // e.g., "_internal" / "assets" / "test_app.exe"
		if shouldOverwrite(f.Name) {
			topPath := filepath.Join(opts.Path, top)
			info, err := os.Stat(topPath)
			if err == nil && !contains(firstInstall, top) {
				var isDir = info.IsDir()
				if contains(overwritePaths, top) && !contains(rollbackDirs, top) {
					os.Rename(topPath, topPath+".bak")
				}
				if isDir {
					if !contains(rollbackDirs, top) {
						rollbackDirs = append(rollbackDirs, top)
					}
				} else {
					rollbackFiles = append(rollbackFiles, top)
				}
			} else {
				firstInstall = append(firstInstall, top)
			}
		}
		if f.FileInfo().IsDir() {
			if !exists(dest) || contains(overwritePaths, top) {
				if err := os.MkdirAll(dest, 0755); err != nil {
					return "", err
				}
			}
			copied += int64(f.UncompressedSize64)
			atomic.StoreInt64(&progressCurrent, copied)
			continue
		}

		if err := os.MkdirAll(filepath.Dir(dest), 0755); err != nil {
			return "", err
		}

		if exists(dest) && !shouldOverwrite(f.Name) {
			copied += int64(f.UncompressedSize64)
			atomic.StoreInt64(&progressCurrent, copied)
			continue
		}

		out, err := os.OpenFile(dest, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
		if err != nil {
			return "", err
		}

		in, err := f.Open()
		if err != nil {
			out.Close()
			return "", err
		}

		buf := make([]byte, 32*1024)
		for {
			n, err := in.Read(buf)
			if n > 0 {
				out.Write(buf[:n])
				copied += int64(n)
				atomic.StoreInt64(&progressCurrent, copied)
			}
			if err == io.EOF {
				break
			}
			if err != nil {
				out.Close()
				in.Close()
				return "", err
			}
		}

		out.Close()
		in.Close()
		time.Sleep(5 * time.Millisecond)
	}

	if len(rollbackFiles)+len(rollbackDirs) > 0 {
		if runtime.GOOS == "windows" {
			writeFile(filepath.Join(opts.Path, "_rollback.bat"),
				rollbackBat(rollbackFiles, rollbackDirs), 0644)
		} else {
			writeFile(filepath.Join(opts.Path, "_rollback.sh"),
				rollbackSh(rollbackFiles, rollbackDirs), 0755)
		}
	}

	atomic.StoreInt32(&progressDone, 1)
	fmt.Println()

	// On Linux/macOS, set exec permission for the main executable
	if runtime.GOOS == "linux" || runtime.GOOS == "darwin" {
		exePath := filepath.Join(opts.Path, appBase)
		if err := os.Chmod(exePath, 0755); err != nil {
			fmt.Fprintf(os.Stderr, "Warning: failed to set exec permission on %s: %v\n", exePath, err)
		}
	}
	return appBase, nil
}

func writeFile(path, content string, mode os.FileMode) error {
	return os.WriteFile(path, []byte(content), mode)
}

func isExecutable(fi os.FileInfo) bool {
	if runtime.GOOS == "windows" {
		return strings.HasSuffix(strings.ToLower(fi.Name()), ".exe")
	}
	return fi.Mode()&0111 != 0
}

func rollbackBat(files, dirs []string) string {
	var b strings.Builder

	b.WriteString("@echo off\nsetlocal\n\nping localhost -n 2 >nul\n\n")

	for _, d := range dirs {
		b.WriteString(fmt.Sprintf(
			`if exist "%[1]s.bak" (
	rmdir /s /q "%[1]s" 2>nul
	rename "%[1]s.bak" "%[1]s"
)
`, d))
	}

	for _, f := range files {
		b.WriteString(fmt.Sprintf(
			`if exist "%[1]s.bak" (
	del "%[1]s" 2>nul
	rename "%[1]s.bak" "%[1]s"
)
`, f))
	}

	b.WriteString("\nstart \"\" \"" + files[0] + "\"\n")
	return b.String()
}

func rollbackSh(files, dirs []string) string {
	var b strings.Builder

	b.WriteString("#!/bin/sh\ncd \"$(dirname \"$0\")\" || exit 1\nsleep 2\n\n")

	for _, d := range dirs {
		b.WriteString(fmt.Sprintf(
			`[ -d "%[1]s.bak" ] && rm -rf "%[1]s" && mv "%[1]s.bak" "%[1]s"
`, d))
	}

	for _, f := range files {
		b.WriteString(fmt.Sprintf(
			`[ -f "%[1]s.bak" ] && rm -f "%[1]s" && mv "%[1]s.bak" "%[1]s" && chmod +x "%[1]s"
`, f))
	}

	b.WriteString("\nexec \"./" + files[0] + "\"\n")
	return b.String()
}

func getTopSegment(path string) string {
	path = strings.ReplaceAll(path, "\\", "/")
	path = strings.TrimPrefix(path, "./")
	parts := strings.Split(path, "/")
	if len(parts) < 2 {
		return ""
	}
	return parts[1] // first segment inside archive: "_internal", "assets", "test_app.exe"
}

func contains(slice []string, s string) bool {
	for _, v := range slice {
		if v == s || strings.HasPrefix(s, v+".") { // handle exe
			return true
		}
	}
	return false
}

// ====================== SHORTCUT ======================

func createShortcut(targetFile string, name string) error {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return err
	}

	desktop := filepath.Join(homeDir, "Desktop")
	startDir := filepath.Dir(targetFile)

	if opts.CreateShortcut {
		switch runtime.GOOS {
		case "windows":
			desktop_shortcut_path := filepath.Join(desktop, name+".lnk")
			if _, err := os.Stat(desktop_shortcut_path); errors.Is(err, os.ErrNotExist) {
				psDesktop := fmt.Sprintf(`$WshShell = New-Object -ComObject WScript.Shell;
				$Shortcut = $WshShell.CreateShortcut("%s");
				$Shortcut.TargetPath = "%s";
				$Shortcut.WorkingDirectory = "%s";
				$Shortcut.Save()`,
					desktop_shortcut_path, targetFile, startDir)
				cmd := exec.Command("powershell", "-Command", psDesktop)
				cmd.Run()
			}
		case "linux", "darwin":
			desktopFile := filepath.Join(desktop, name+".desktop")
			if _, err := os.Stat(desktopFile); errors.Is(err, os.ErrNotExist) {
				content := fmt.Sprintf(`[Desktop Entry]
				Name=%s
				Exec=%s
				Type=Application
				Terminal=false
				`, name, targetFile)
				if err := os.WriteFile(desktopFile, []byte(content), 0755); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

// ======================= MAIN =========================

func main() {
	target, err := os.Getwd()
	if err != nil {
		abort("Cannot get current directory: " + err.Error())
	}

	exeName, err := extractPayload(target)

	if opts.ShortcutName == "" {
		opts.ShortcutName = exeName
	}

	if err != nil {
		abort("Install failed: " + err.Error())
	}

	appDir := opts.Path

	if runtime.GOOS == "windows" {
		exeName += ".exe"
	}

	exe := filepath.Join(appDir, exeName)
	exe, _ = filepath.Abs(exe)
	fmt.Println("Installed executable:", exe)

	createShortcut(exe, opts.ShortcutName)

	cmd := exec.Command(exe)
	cmd.Dir = appDir
	if opts.Console {
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin
	} else {
		cmd.Stdout = nil
		cmd.Stderr = nil
		cmd.Stdin = nil
	}

	// if runtime.GOOS == "windows" {
	// 	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: false}
	// }

	err = cmd.Start()
	if err != nil {
		abort("Failed to start executable: " + err.Error())
	}

	fmt.Println("Application launched, exiting installer")
}
