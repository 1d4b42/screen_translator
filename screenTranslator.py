import os
import threading
import time
import mss
import pytesseract
import tkinter as tk
from googletrans import Translator
from PIL import Image
from multiprocessing import Process, Queue, get_context
import textwrap

class Main():
    def __init__(self, lang='eng', input='en', output='ja', kanjiflag=False):
        
        self.TESSERACT_PATH = 'C:\\Tesseract'
        self.TESSDATA_PATH = 'C:\\Tesseract\\tessdata'
        os.environ["PATH"] += os.pathsep + self.TESSERACT_PATH
        os.environ["TESSDATA_PREFIX"] = self.TESSDATA_PATH
        self.inputs = []
        self.stop_capture = False
        self.top = 0
        self.left = 0
        self.text_before = ""
        self.lang = lang
        self.input = input
        self.output = output
        self.kanjiflag = kanjiflag

    def image_to_text(self, image, lang='eng'):
        text = pytesseract.image_to_string(image, lang=lang)
        return text

    def i2t_screen(self, screen, mnt, lang='eng'):
        img = screen.grab(mnt)
        pmap = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        text = self.image_to_text(pmap, lang=lang)
        return text

    def dummy_screen(self, width: int, height: int):
        root = tk.Tk()
        root.title("Press Enter to start")
        root.geometry(f"{width}x{height}")
        root.resizable(True, True)
        root.attributes("-alpha", 0.8)
        root.configure(bg="black")

        def destroy(event):
            root.destroy()
        
        root.bind("<Return>", destroy)

        def update_geometry(event):
            global top, left, w, h
            top = root.winfo_y()
            left = root.winfo_x()
            w = root.winfo_width()
            h = root.winfo_height()
        
        root.bind("<Configure>", update_geometry)
        root.mainloop()
        return {"top": int(top), "left": int(left), "width": int(w), "height": int(h)}

    def translate_f(self, text_before, src='en', dest='ja'):
        translator = Translator()
        try:
            txt = translator.translate(text_before, src=src, dest=dest).text
        except Exception as e:
            txt = text_before
        return txt

    def kanji_f(self, text_before):
        from pykakasi import kakasi
        ka = kakasi()
        text_after = ""
        text_en_sentences = text_before.split('\n')
        for sentence in text_en_sentences:
            result = ka.convert(sentence)
            text_after += ''.join([item['hira'] for item in result]) + '\n'
        return text_after

    def remove_linebreaks(self, text):
        return text.replace('\n', ' ')

    def reinsert_linebreaks(self, original, translated):
        original_lines = original.split('\n')
        words = translated.split()
        translated_lines = []
        index = 0
        for line in original_lines:
            length = len(line.split())
            translated_lines.append(' '.join(words[index:index+length]))
            index += length
        return '\n'.join(translated_lines)
    
    @staticmethod
    def wrap_text(text, width):
        return '\n'.join(textwrap.fill(line, width) for line in text.split('\n'))

    @staticmethod
    def translation_process(queue, fps_queue, close_queue, lang, input_lang, output_lang, kanjiflag, mnt):
        sct = mss.mss()
        main = Main(lang=lang, input=input_lang, output=output_lang, kanjiflag=kanjiflag)
        while True:
            if not close_queue.empty():
                break
            start_time = time.time()
            text_before = main.i2t_screen(sct, mnt, lang=lang)
            text_after = ""
            if not kanjiflag:
                text_no_breaks = main.remove_linebreaks(text_before)
                translated_text = main.translate_f(text_no_breaks, src=input_lang, dest=output_lang)
                text_after = main.reinsert_linebreaks(text_before, translated_text)
            else:
                text_after = main.kanji_f(text_before)
            queue.put([text_before, text_after], block=False)
            fps = 1 / (time.time() - start_time)
            fps_queue.put(fps)

    @staticmethod
    def display_process(queue, fps_queue, mnt):
        width_tmp = mnt["width"]
        height_tmp = mnt["height"] * 2
        top_tmp = mnt["top"]
        left_tmp = mnt["left"]

        root = tk.Tk()
        root.title("Press Enter to Exit")
        root.geometry(f"{width_tmp}x{height_tmp}+{left_tmp}+{top_tmp}")
        root.resizable(True, True)
        root.attributes("-alpha", 1)
        root.configure(bg="white")

        canvas = tk.Canvas(root, width=width_tmp, height=height_tmp/2, highlightthickness=0)
        canvas_translated = tk.Canvas(root, width=width_tmp, height=height_tmp/2, highlightthickness=0)
        canvas_translated.place(y=height_tmp/2)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        canvas_translated.grid(row=1, column=0, sticky="nsew")

        label = tk.Label(root)
        fps_label = tk.Label(root, text="FPS: 0")
        label.grid(row=0,column=1)
        fps_label.grid(row=1,column=1)

        def on_closing():
            root.quit()

        def update_display():
            txt_list_before = ["", ""]
            while True:
                txt_list = queue.get()
                if txt_list == None:
                    print("[W] queue is empty\n")
                    continue
                if txt_list[0] != txt_list_before[0]:
                    txt_list_before = txt_list
                    canvas.delete("OUTPUT")
                    canvas_translated.delete("OUTPUT")
                    wrap_width = int(canvas.winfo_width() / 12)
                    wrapped_text_before = Main.wrap_text(txt_list[0], wrap_width)
                    wrapped_text_after = Main.wrap_text(txt_list[1], wrap_width)
                    canvas.create_text(10, 10, text=wrapped_text_before, fill="black", tag="OUTPUT", anchor="nw")
                    canvas_translated.create_text(10, 10, text=wrapped_text_after, fill="black", tag="OUTPUT", anchor="nw")
                    canvas.update()
                if not fps_queue.empty():
                    fps_label.config(text=f"FPS: {fps_queue.get(block=False):.2f}")
                time.sleep(0.0005)

        root.protocol("WM_DELETE_WINDOW", on_closing)
        display_thread = threading.Thread(target=update_display, daemon=True)
        display_thread.start()
        root.mainloop()

    def app(self):
        self.mnt = self.dummy_screen(512, 512)
        
        ctx = get_context('spawn')
        queue = ctx.Queue()
        fps_queue = ctx.Queue()
        close_queue = Queue()

        process1 = ctx.Process(
            target=self.translation_process,
            args=(
                queue,
                fps_queue,
                close_queue,
                self.lang,
                self.input,
                self.output,
                self.kanjiflag,
                self.mnt
            ),
        )
        process1.start()

        process2 = ctx.Process(
            target=self.display_process,
            args=(
                queue,
                fps_queue,
                self.mnt
            ),
        )
        process2.start()

        process2.join()
        close_queue.put(True)
        process1.join(5)
        if process1.is_alive():
            process1.terminate()
        process1.join()


if __name__ == "__main__":
    import fire
    fire.Fire(Main)
