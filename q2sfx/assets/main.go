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
	"syscall"
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
	// zip paths всегда используют '/'
	parts := strings.Split(zipPath, "/")

	// ожидаем: appBase/...
	if len(parts) < 2 {
		return false
	}

	top := parts[1] // assets, _internal, appBase.exe

	for _, p := range overwritePaths {
		if top == p {
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

	// base name проекта = имя архива без .zip
	appBase := strings.TrimSuffix(zipName, ".zip")

	overwritePaths = []string{"_internal", "assets", appBase}

	if opts.Path == "" {
		opts.Path = appBase
	}

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

	var copied int64
	for _, f := range z.File {
		dest := filepath.Join(opts.Path, stripFirstSegment(f.Name))

		if f.FileInfo().IsDir() {
			if !exists(dest) || shouldOverwrite(f.Name) {
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
	atomic.StoreInt32(&progressDone, 1)
	fmt.Println()
	return appBase, nil
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
	fmt.Println("Target directory    :", appDir)
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

	if runtime.GOOS == "windows" {
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: false}
	}

	err = cmd.Start()
	if err != nil {
		abort("Failed to start executable: " + err.Error())
	}

	fmt.Println("Application launched, exiting installer")
}
