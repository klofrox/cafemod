"""Build the TFMProxyLoader with the Café "Sil" menu item and the dark theme.

    python tools/cafe_sil_loader/build.py            # -> build/TFMProxyLoader_sil.swf
    python tools/cafe_sil_loader/build.py --install  # and copy it into Steam's Transformice

The base is tfm-proxy-loader v1.6.32 (MIT, github.com/friedkeenan/tfm-proxy-loader).
ffdec decompiles it, the scripts below are patched, and ffdec compiles them
back in. The game itself is never modified: the loader adds "Sil" to the Café
post menu at runtime and sends "BLOCK <name>" to transformice.cafe_block_proxy,
which must be running (it is also the proxy the loader connects the game to).

Steam's original Transformice.swf is kept as Transformice.swf.orig; copy it
back to undo.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = HERE / "TFMProxyLoader-1.6.32.swf"
INJECT = HERE / "cafe_sil.as"
THEME = HERE / "dark_theme.as"
FLAT = HERE / "flat_ui.as"
PANEL = HERE / "cafe_panel.as"
GIF = HERE / "gif_avatar.as"
EXTRA = HERE / "cafe_extra.as"
FFDEC = ROOT / "local_assets" / "tools" / "ffdec_26.5.0" / "ffdec.jar"
OUT = ROOT / "build" / "TFMProxyLoader_sil.swf"
STEAM = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Transformice")

LOG = "TFMProxyLoader.cs_static_log"


def _replace(text, old, new, what):
    if text.count(old) != 1:
        raise SystemExit(f"{what}: expected one match, found {text.count(old)} - the base loader changed?")
    return text.replace(old, new)


def patch_main(src):
    """TFMProxyLoader.as: the Sil code, its imports, and a decompiler fix."""
    src = _replace(src, """   import flash.display.Sprite;
   import flash.events.KeyboardEvent;""", """   import flash.desktop.Clipboard;
   import flash.desktop.ClipboardFormats;
   import flash.display.Bitmap;
   import flash.display.BitmapData;
   import flash.display.PNGEncoderOptions;
   import flash.events.SampleDataEvent;
   import flash.media.Sound;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.Graphics;
   import flash.display.InteractiveObject;
   import flash.display.Loader;
   import flash.display.Shape;
   import flash.display.Sprite;
   import flash.events.Event;
   import flash.events.IOErrorEvent;
   import flash.filters.DropShadowFilter;
   import flash.filters.GlowFilter;
   import flash.geom.ColorTransform;
   import flash.geom.Matrix;
   import flash.geom.Rectangle;
   import flash.events.KeyboardEvent;
   import flash.events.MouseEvent;
   import flash.events.ProgressEvent;
   import flash.events.SecurityErrorEvent;
   import flash.net.Socket;
   import flash.net.URLRequest;
   import flash.system.ApplicationDomain;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import flash.text.TextFormat;
   import flash.utils.getDefinitionByName;
   import flash.utils.ByteArray;
   import flash.utils.describeType;
   import flash.utils.getQualifiedClassName;
   import flash.utils.getTimer;
   import flash.utils.setTimeout;""", "imports")
    src = _replace(src, """         this.stage.addEventListener("keyDown",this.load_last_game);
      }
""", """         this.stage.addEventListener("keyDown",this.load_last_game);
         this.cs_init();
      }
""" + INJECT.read_text(encoding="utf-8") + THEME.read_text(encoding="utf-8") + FLAT.read_text(encoding="utf-8") + PANEL.read_text(encoding="utf-8") + GIF.read_text(encoding="utf-8")
      + EXTRA.read_text(encoding="utf-8"), "constructor")
    # The decompiler typed the game loader instance as Class: recompiled, that
    # throws TypeError #1034 when a game is picked (green screen).
    src = _replace(src, "var _loc2_:Class = new param1();", "var _loc2_:* = new param1();", "load_game")
    return src


def patch_game_loader(src):
    """GameLoader.as: progress lines in the proxy log, and compile fixes."""
    src = _replace(src, """         var _loc2_:URLLoader = new URLLoader();
         _loc2_.dataFormat = "binary";""", f"""         {LOG}("downloading " + this.game_url + " steam=" + this.steam_okay);
         var _loc2_:URLLoader = new URLLoader();
         _loc2_.dataFormat = "binary";
         _loc2_.addEventListener("ioError",function(e:*):void
         {{
            {LOG}("download failed: " + e);
         }});
         _loc2_.addEventListener("securityError",function(e:*):void
         {{
            {LOG}("download security error: " + e);
         }});""", "download")
    src = _replace(src, """         this.final_loader = new Loader();
         this.final_loader.contentLoaderInfo.addEventListener("complete",this.game_code_loaded);""", f"""         {LOG}("downloaded " + URLLoader(param1.currentTarget).bytesLoaded + " bytes");
         this.final_loader = new Loader();
         this.final_loader.contentLoaderInfo.addEventListener("complete",this.game_code_loaded);
         this.final_loader.contentLoaderInfo.addEventListener("ioError",function(e:*):void
         {{
            {LOG}("game code failed to load: " + e);
         }});""", "downloaded")
    src = _replace(src, """      private function game_code_loaded(param1:Event) : void
      {""", f"""      private function game_code_loaded(param1:Event) : void
      {{
         {LOG}("game code loaded");""", "game code")
    src = _replace(src, """                     this.logging_class_info = {""", f"""                     {LOG}("logging class found");
                     this.logging_class_info = {{""", "logging class")
    src = _replace(src, """                           this.addEventListener("enterFrame",this.try_replace_connection);
                           return;""", f"""                           {LOG}("connection class found");
                           this.addEventListener("enterFrame",this.try_replace_connection);
                           return;""", "connection class")
    # Hand the game's classes to the dark theme as soon as the game is running.
    src = _replace(src, """         var _loc5_:ApplicationDomain = _loc2_.contentLoaderInfo.applicationDomain;""", """         var _loc5_:ApplicationDomain = _loc2_.contentLoaderInfo.applicationDomain;
         TFMProxyLoader.cs_static_game(_loc5_);""", "game domain")
    src = _replace(src, """      private function loaded_socket_wrapper(param1:Event) : void
      {""", f"""      private function loaded_socket_wrapper(param1:Event) : void
      {{
         {LOG}("socket wrapper built");""", "socket wrapper")
    src = _replace(src, """         this.removeEventListener("enterFrame",this.try_replace_connection);
      }""", f"""         this.removeEventListener("enterFrame",this.try_replace_connection);
         {LOG}("connection replaced: game -> proxy, real server " + this.main_address + " " + this.main_ports);
      }}""", "connection replaced")
    # ffdec's compiler rejects these decompiled calls on an untyped object.
    src = src.replace("this.steamworks.init()", 'this.steamworks["init"]()')
    src = src.replace("this.steamworks.dispose()", 'this.steamworks["dispose"]()')
    # The decompiler drops some imports the code uses.
    head, sep, rest = src.partition("public class")
    for imp in ("flash.display.DisplayObject", "flash.display.DisplayObjectContainer", "flash.display.Loader",
                "flash.events.Event", "flash.system.ApplicationDomain", "flash.system.LoaderContext",
                "flash.net.URLRequest", "flash.net.Socket", "flash.utils.ByteArray", "flash.utils.describeType"):
        if f"import {imp};" not in head:
            head = head.replace("{\n", "{\n   import " + imp + ";\n", 1)
    return head + sep + rest


def ffdec(*args):
    result = subprocess.run(["java", "-jar", str(FFDEC), *map(str, args)], capture_output=True, text=True)
    errors = [line for line in (result.stdout + result.stderr).splitlines() if "SEVERE" in line]
    if result.returncode != 0 or errors:
        raise SystemExit("ffdec failed:\n" + "\n".join(errors or [result.stderr[-2000:]]))


def build(out=OUT):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ffdec("-export", "script", tmp / "src", BASE)
        scripts = tmp / "src" / "scripts"
        patch = tmp / "patch" / "scripts"
        (patch / "loaders").mkdir(parents=True)
        main = (scripts / "TFMProxyLoader.as").read_text(encoding="utf-8")
        (patch / "TFMProxyLoader.as").write_text(patch_main(main), encoding="utf-8")
        loader = (scripts / "loaders" / "GameLoader.as").read_text(encoding="utf-8")
        (patch / "loaders" / "GameLoader.as").write_text(patch_game_loader(loader), encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        ffdec("-importScript", BASE, out, tmp / "patch")
    print(f"built {out} ({out.stat().st_size} bytes)")
    return out


def install(swf, steam=STEAM):
    target = steam / "Transformice.swf"
    backup = steam / "Transformice.swf.orig"
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"original kept as {backup}")
    shutil.copy2(swf, target)
    print(f"installed into {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--install", action="store_true", help="copy into Steam's Transformice folder")
    args = parser.parse_args()
    if not FFDEC.exists():
        sys.exit(f"ffdec not found at {FFDEC}")
    built = build(args.out)
    if args.install:
        install(built)
