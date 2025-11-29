import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import fitz  # PyMuPDF
from pydub import AudioSegment
import os

# --- GLOBAL VERILER ---

selected_files = []
output_dir = ""


# --- YARDIMCI FONKSIYONLAR ---

def safe_output_path(base_dir, base_name, ext):
    """Aynı isim varsa _1, _2... ekleyerek güvenli çıktı yolu üretir."""
    ext = ext.lstrip(".")
    candidate = os.path.join(base_dir, f"{base_name}.{ext}")
    if not os.path.exists(candidate):
        return candidate

    i = 1
    while True:
        candidate = os.path.join(base_dir, f"{base_name}_{i}.{ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


def update_file_count():
    label_file_count.config(text=f"{len(selected_files)} dosya seçili.")


# --- LISTE ISLEMLERI ---

def add_files():
    filetypes = [
        ("Tüm desteklenen", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.pdf;*.mp3;*.wav;*.ogg;*.flac"),
        ("Resimler", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
        ("PDF", "*.pdf"),
        ("Ses", "*.mp3;*.wav;*.ogg;*.flac"),
        ("Tüm dosyalar", "*.*"),
    ]
    files = filedialog.askopenfilenames(title="Dosya seç", filetypes=filetypes)
    if not files:
        return

    for f in files:
        if f not in selected_files:
            selected_files.append(f)
            listbox_files.insert(tk.END, f)

    update_file_count()


def remove_selected_file():
    selection = listbox_files.curselection()
    if not selection:
        return
    index = selection[0]
    listbox_files.delete(index)
    del selected_files[index]
    update_file_count()


def clear_file_list():
    listbox_files.delete(0, tk.END)
    selected_files.clear()
    update_file_count()


def select_output_dir():
    global output_dir
    directory = filedialog.askdirectory(title="Çıktı klasörünü seç")
    if directory:
        output_dir = directory
        label_output.config(text=f"Çıktı klasörü: {output_dir}")
    else:
        label_output.config(text="Çıktı klasörü seçilmedi.")


def get_resize_values():
    """Genişlik / yükseklik alanlarındaki değerleri int olarak döndür (veya None)."""
    w_text = entry_width.get().strip()
    h_text = entry_height.get().strip()
    width = None
    height = None

    if w_text:
        try:
            w_val = int(w_text)
            if w_val > 0:
                width = w_val
        except ValueError:
            pass

    if h_text:
        try:
            h_val = int(h_text)
            if h_val > 0:
                height = h_val
        except ValueError:
            pass

    return width, height


# --- DÖNÜŞTÜRME FONKSIYONLARI ---

def convert_image_format(input_path, out_dir, target_format, width=None, height=None, quality=None):
    """Resim format dönüştürme + opsiyonel resize + kalite (jpeg sıkıştırma)."""
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_path = safe_output_path(out_dir, base_name, target_format)

    with Image.open(input_path) as img:
        # Yeniden boyutlandırma
        if width and height:
            img = img.resize((width, height), Image.LANCZOS)

        # JPG için mod dönüşümü
        if target_format.lower() in ["jpg", "jpeg"] and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        save_params = {}
        if target_format.lower() in ["jpg", "jpeg"] and quality:
            save_params["quality"] = quality
            save_params["optimize"] = True

        img.save(out_path, target_format.upper(), **save_params)

    return out_path


def convert_pdf_to_images(pdf_path, out_dir, target_format):
    """PDF'i sayfa sayfa resme dönüştürür."""
    doc = fitz.open(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    for page_index in range(len(doc)):
        page = doc[page_index]
        pix = page.get_pixmap()
        page_name = f"{base_name}_page_{page_index + 1}"
        out_path = safe_output_path(out_dir, page_name, target_format)
        pix.save(out_path)

    doc.close()
    return True


def images_to_pdf(paths, out_dir):
    """Listeden resimleri tek bir PDF'e dönüştürür."""
    image_paths = [
        p for p in paths
        if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))
    ]

    if not image_paths:
        raise ValueError("Listede PDF'e dönüştürülebilecek resim yok.")

    images = []
    for p in image_paths:
        img = Image.open(p)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        images.append(img)

    # İlk resmin adına göre çıktı ismi verelim
    first_name = os.path.splitext(os.path.basename(image_paths[0]))[0]
    out_pdf_path = safe_output_path(out_dir, first_name + "_merged", "pdf")

    first, *rest = images
    first.save(out_pdf_path, save_all=True, append_images=rest)

    for img in images:
        img.close()

    return out_pdf_path


def convert_audio(input_path, out_dir, target_format):
    """Ses dönüştürme (mp3, wav, ogg, flac vs.) – ffmpeg kuruluyken çalışır."""
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_path = safe_output_path(out_dir, base_name, target_format)

    audio = AudioSegment.from_file(input_path)
    audio.export(out_path, format=target_format)
    return out_path


# --- FORMAT MENÜSÜNÜ GÜNCELLEME ---

def update_format_options():
    """Seçilen işleme göre hedef format listesini günceller."""
    op = operation_var.get()
    if op == "Resim format dönüştür":
        formats = ["png", "jpg", "webp"]
    elif op == "PDF -> Resim":
        formats = ["png", "jpg"]
    elif op == "Resim(ler) -> PDF":
        formats = ["pdf"]
    elif op == "Ses format dönüştür":
        formats = ["mp3", "wav", "ogg", "flac"]
    else:
        formats = ["txt"]

    menu = format_menu["menu"]
    menu.delete(0, "end")
    for f in formats:
        menu.add_command(label=f, command=lambda value=f: format_var.set(value))
    format_var.set(formats[0])


# --- ANA DÖNÜŞTÜRME BUTONUNUN ISLEVI ---

def start_conversion():
    if not selected_files:
        messagebox.showwarning("Uyarı", "Lütfen en az bir dosya ekleyin.")
        return

    if not output_dir:
        messagebox.showwarning("Uyarı", "Lütfen çıktı klasörünü seçin.")
        return

    op = operation_var.get()
    target_format = format_var.get().lower()

    width, height = get_resize_values()
    quality = quality_scale.get()

    success = 0
    errors = 0

    try:
        if op == "Resim format dönüştür":
            for path in selected_files:
                try:
                    convert_image_format(path, output_dir, target_format, width, height, quality)
                    success += 1
                except Exception as e:
                    print("Resim dönüştürürken hata:", path, e)
                    errors += 1

        elif op == "PDF -> Resim":
            for path in selected_files:
                if not path.lower().endswith(".pdf"):
                    print("PDF değil, atlandı:", path)
                    continue
                try:
                    convert_pdf_to_images(path, output_dir, target_format)
                    success += 1
                except Exception as e:
                    print("PDF -> Resim hatası:", path, e)
                    errors += 1

        elif op == "Resim(ler) -> PDF":
            try:
                images_to_pdf(selected_files, output_dir)
                success = 1
            except Exception as e:
                print("Resim(ler) -> PDF hatası:", e)
                errors = 1

        elif op == "Ses format dönüştür":
            for path in selected_files:
                try:
                    convert_audio(path, output_dir, target_format)
                    success += 1
                except Exception as e:
                    print("Ses dönüştürme hatası:", path, e)
                    errors += 1

        else:
            messagebox.showerror("Hata", "Geçersiz işlem türü.")
            return

    finally:
        messagebox.showinfo("Tamamlandı", f"Başarılı: {success}\nHatalı: {errors}")


# --- ARAYÜZ ---

root = tk.Tk()
root.title("Gelişmiş Dosya Converter (Video Yok)")
root.geometry("750x550")

# İşlem türü
tk.Label(root, text="İşlem türü:").pack(pady=(10, 0))

operation_var = tk.StringVar(value="Resim format dönüştür")
operation_menu = tk.OptionMenu(
    root,
    operation_var,
    "Resim format dönüştür",
    "PDF -> Resim",
    "Resim(ler) -> PDF",
    "Ses format dönüştür",
)
operation_menu.pack()

# Hedef format
tk.Label(root, text="Hedef format:").pack(pady=(10, 0))

format_var = tk.StringVar()
format_menu = tk.OptionMenu(root, format_var, "")
format_menu.pack()

# Resize + kalite ayarları
frame_resize = tk.Frame(root)
frame_resize.pack(pady=10)

tk.Label(frame_resize, text="Genişlik (px):").grid(row=0, column=0, padx=5)
entry_width = tk.Entry(frame_resize, width=7)
entry_width.grid(row=0, column=1, padx=5)

tk.Label(frame_resize, text="Yükseklik (px):").grid(row=0, column=2, padx=5)
entry_height = tk.Entry(frame_resize, width=7)
entry_height.grid(row=0, column=3, padx=5)

tk.Label(frame_resize, text="Kalite (sadece JPG):").grid(row=1, column=0, columnspan=2, pady=(5, 0))
quality_scale = tk.Scale(frame_resize, from_=10, to=95, orient=tk.HORIZONTAL)
quality_scale.set(85)
quality_scale.grid(row=1, column=2, columnspan=2, padx=5)

# Dosya listesi ve butonlar
frame_files = tk.Frame(root)
frame_files.pack(pady=10, fill=tk.BOTH, expand=True)

btn_add_files = tk.Button(frame_files, text="Dosya Ekle", command=add_files)
btn_add_files.grid(row=0, column=0, padx=5, pady=5, sticky="w")

btn_remove_file = tk.Button(frame_files, text="Seçiliyi Sil", command=remove_selected_file)
btn_remove_file.grid(row=0, column=1, padx=5, pady=5, sticky="w")

btn_clear_files = tk.Button(frame_files, text="Listeyi Temizle", command=clear_file_list)
btn_clear_files.grid(row=0, column=2, padx=5, pady=5, sticky="w")

listbox_files = tk.Listbox(frame_files, width=90, height=12)
listbox_files.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

frame_files.rowconfigure(1, weight=1)
frame_files.columnconfigure(0, weight=1)

label_file_count = tk.Label(frame_files, text="0 dosya seçili.")
label_file_count.grid(row=2, column=0, columnspan=3, sticky="w", padx=5)

# Çıktı klasörü
frame_output = tk.Frame(root)
frame_output.pack(pady=10, fill=tk.X)

btn_output_dir = tk.Button(frame_output, text="Çıktı klasörünü seç", command=select_output_dir)
btn_output_dir.pack(side=tk.LEFT, padx=5)

label_output = tk.Label(frame_output, text="Çıktı klasörü seçilmedi.")
label_output.pack(side=tk.LEFT, padx=5)

# Dönüştür butonu
btn_convert = tk.Button(root, text="Dönüştür", command=start_conversion)
btn_convert.pack(pady=10)

# İşlem türü değişince format listesini güncelle
def on_operation_change(*args):
    update_format_options()

operation_var.trace_add("write", on_operation_change)
update_format_options()  # başlangıçta doldur

root.mainloop()
