using System;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using Microsoft.Win32;

namespace AciBolACPredimensionamiento
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string exeName = Path.GetFileName(Application.ExecutablePath);
                using (RegistryKey key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION"))
                {
                    if (key != null) key.SetValue(exeName, 11001, RegistryValueKind.DWord);
                }
            }
            catch { }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    public class MainForm : Form
    {
        private readonly WebBrowser browser;

        public MainForm()
        {
            Text = "AciBolAC - Predimensionamiento Estructural";
            Width = 1200;
            Height = 800;
            MinimumSize = new System.Drawing.Size(1000, 700);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = System.Drawing.Color.FromArgb(24, 36, 42);
            Icon = System.Drawing.Icon.ExtractAssociatedIcon(Application.ExecutablePath);

            browser = new WebBrowser();
            browser.Dock = DockStyle.Fill;
            browser.ScriptErrorsSuppressed = true;
            browser.IsWebBrowserContextMenuEnabled = false;
            browser.WebBrowserShortcutsEnabled = false;
            Controls.Add(browser);

            Load += delegate { browser.DocumentText = LoadEmbeddedHtml(); };
        }

        private static string LoadEmbeddedHtml()
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            using (Stream stream = asm.GetManifestResourceStream("index.html"))
            {
                if (stream == null) return "<html><body><h1>No se encontro la interfaz embebida.</h1></body></html>";
                using (StreamReader reader = new StreamReader(stream)) return reader.ReadToEnd();
            }
        }
    }
}
