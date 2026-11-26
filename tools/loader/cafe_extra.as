
      // ---- Café extras: post style, notes, mentions, link previews, search, chime, screenshots ----
      //
      // The game colours every name from a hash of it; the post's text is set
      // as HTML starting with that colour. Every few frames each post of the
      // open Café is drawn again from the game's text: white name, the
      // player's private note after it, a highlight when it names this
      // player. A post is redone when the game redraws it (a like) or when
      // the state changes (a new note).

      private static const CX_NAME_COLOUR:RegExp = /^(<font color=['"]#)([0-9a-fA-F]{1,6})(['"]>)/i;

      private static const CX_WHITE:String = "FFFFFF";

      private static const CX_TAGS:RegExp = /<[^>]*>/g;

      private static const CX_AUTHOR:RegExp = /[^\s#]+(#\d{4})?/;

      private static const CX_LINK:RegExp = /(https?:\/\/)?((www|i|files|image)\.)?(prnt\.sc|prntscr\.com|imgur\.com|catbox\.moe)\/[^\s<>"']+/gi;

      private var cx_frames:int = 0;

      private var cx_whitened:int = 0;

      private var cx_chime:Vector.<Number> = null;

      public var cx_ver:int = 0;

      private var cx_posts:Dictionary = new Dictionary(true);

      private var cx_cards:Dictionary = new Dictionary(true);

      private var cx_marks:Dictionary = new Dictionary(true);

      public var cx_results:Array = [];

      public var cx_searched:Boolean = false;

      private var cx_query:String = "";

      public var cx_note_for:String = "";

      private var cx_note_text:String = "";

      private var cx_thumbs:Object = {};

      private var cx_popup:Sprite = null;

      private var cx_popup_url:String = null;

      private function cx_start() : void
      {
         this.stage.addEventListener(Event.ENTER_FRAME,this.cx_tick);
         this.stage.addEventListener(MouseEvent.MOUSE_MOVE,this.cx_on_move,false,0,true);
      }

      private function cx_tick(e:Event) : void
      {
         var win:DisplayObjectContainer = this.cp_cafe;
         if(++this.cx_frames % 10 != 0 || win == null || win.stage == null)
         {
            return;
         }
         try
         {
            this.cx_whiten(win,0);
            if(this.cx_goto_post != 0)
            {
               this.cx_try_goto();
            }
         }
         catch(err:Error)
         {
         }
      }

      private function cx_whiten(c:DisplayObjectContainer, depth:int) : void
      {
         var i:int = 0;
         var d:DisplayObject = null;
         var tf:TextField = null;
         var h:String = null;
         var entry:Object = null;
         for(i = 0; i < c.numChildren; i++)
         {
            d = c.getChildAt(i);
            tf = d as TextField;
            if(tf != null)
            {
               if(tf.styleSheet == null)
               {
                  continue;
               }
               h = tf.htmlText;
               entry = this.cx_posts[tf];
               if(entry != null && h == entry.out)
               {
                  if(entry.ver == this.cx_ver)
                  {
                     continue;
                  }
                  h = entry.orig;
               }
               else if(!CX_NAME_COLOUR.test(h))
               {
                  continue;
               }
               this.cx_render(tf,h);
               if(this.cx_whitened++ == 0)
               {
                  this.cs_log("names: first Café name made white");
               }
            }
            else if(depth < 12 && d is DisplayObjectContainer && d != this.cp_panel)
            {
               this.cx_whiten(DisplayObjectContainer(d),depth + 1);
            }
         }
      }

      private static function cx_escape(s:String) : String
      {
         return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      }

      public function cx_note(name:String) : String
      {
         var notes:Object = this.cp_state.notes;
         var k:String = null;
         if(notes == null || name == null)
         {
            return "";
         }
         for(k in notes)
         {
            if(k.toLowerCase() == name.toLowerCase())
            {
               return String(notes[k]);
            }
         }
         return "";
      }

      private function cx_render(tf:TextField, orig:String) : void
      {
         var m:Object = CX_NAME_COLOUR.exec(orig);
         if(m == null)
         {
            return;
         }
         var white:String = m[1] + CX_WHITE + m[3] + orig.substring(String(m[0]).length);
         var nl:int = white.indexOf("\n");
         var plain:String = orig.replace(CX_TAGS,"");
         var a:Object = CX_AUTHOR.exec(nl >= 0 ? orig.substring(0,orig.indexOf("\n")).replace(CX_TAGS,"") : plain);
         var author:String = a != null ? String(a[0]) : "";
         var note:String = this.cx_note(author);
         if(note != "" && nl >= 0)
         {
            white = white.substring(0,nl) + "  <font size='10' color='#F2C85B'>" + cx_escape(note) + "</font>" + white.substring(nl);
         }
         this.cx_restyle(tf,white);
         this.cx_posts[tf] = {"orig":orig,"out":tf.htmlText,"ver":this.cx_ver};
         if(tf.parent != null)
         {
            this.cx_cards[tf.parent] = tf;
         }
         var me:String = String(this.cp_state.me || "");
         var base:String = me.split("#")[0].toLowerCase();
         var named:Boolean = base != "" && author.toLowerCase() != me.toLowerCase() && new RegExp("@" + base.replace(/[\\^$.*+?()\[\]{}|]/g,"\\$&") + "(?![\\wçğıöşüÇĞİÖŞÜ])","i").test(plain.substring(plain.indexOf("\n") + 1));
         this.cx_mark(tf,named);
      }

      // A post that names this player: a gold tint and a bar on its left (like Discord).
      private function cx_mark(tf:TextField, on:Boolean) : void
      {
         var old:Shape = this.cx_marks[tf] as Shape;
         if(old != null && old.parent != null)
         {
            old.parent.removeChild(old);
         }
         delete this.cx_marks[tf];
         var card:DisplayObjectContainer = tf.parent;
         if(!on || card == null)
         {
            return;
         }
         var b:Rectangle = card.getBounds(card);
         var s:Shape = new Shape();
         s.graphics.beginFill(0xF0B232,0.09);
         s.graphics.drawRect(0,0,b.right,b.bottom);
         s.graphics.endFill();
         s.graphics.beginFill(0xF0B232,1);
         s.graphics.drawRect(0,0,3,b.bottom);
         s.graphics.endFill();
         card.addChildAt(s,0);
         this.cx_marks[tf] = s;
      }

      public function cx_mention(rest:String) : void
      {
         var parts:Array = rest.split("\t");
         this.cx_ding();
         this.cp_toast(parts[0] + " sana yazdı" + (parts.length > 1 && parts[1] != "" ? ": " + parts[1] : ""));
      }

      // ---- link previews: hover a catbox / imgur / prnt.sc link ----

      private function cx_on_move(e:MouseEvent) : void
      {
         var d:DisplayObject = e.target as DisplayObject;
         var tf:TextField = null;
         var depth:int = 0;
         var url:String = null;
         var idx:int = 0;
         var m:Object = null;
         if(this.cp_cafe == null || this.cp_cafe.stage == null)
         {
            this.cx_hide_preview();
            return;
         }
         while(d != null && depth < 4 && tf == null)
         {
            if(d is TextField && this.cx_posts[d] != null)
            {
               tf = TextField(d);
            }
            else if(this.cx_cards[d] != null)
            {
               tf = this.cx_cards[d] as TextField;
            }
            d = d.parent;
            depth++;
         }
         if(tf != null)
         {
            idx = tf.getCharIndexAtPoint(tf.mouseX,tf.mouseY);
            if(idx >= 0)
            {
               CX_LINK.lastIndex = 0;
               while((m = CX_LINK.exec(tf.text)) != null)
               {
                  if(idx >= m.index && idx < m.index + String(m[0]).length)
                  {
                     url = String(m[0]).replace(/[.,!?)\]]+$/,"");
                     break;
                  }
               }
            }
         }
         if(url == null)
         {
            this.cx_hide_preview();
            return;
         }
         if(url.indexOf("http") != 0)
         {
            url = "https://" + url;
         }
         this.cx_show_preview(url,e.stageX,e.stageY);
      }

      private function cx_hide_preview() : void
      {
         if(this.cx_popup != null && this.cx_popup.parent != null)
         {
            this.cx_popup.parent.removeChild(this.cx_popup);
         }
         this.cx_popup = null;
         this.cx_popup_url = null;
      }

      private function cx_show_preview(url:String, x:Number, y:Number) : void
      {
         var thumb:* = this.cx_thumbs[url];
         var p:Sprite = null;
         var t:TextField = null;
         var bmp:Bitmap = null;
         if(this.cx_popup_url != url || this.cx_popup == null)
         {
            this.cx_hide_preview();
            if(thumb == null)
            {
               this.cx_thumbs[url] = "wait";
               this.cs_send("PREVIEW " + url);
               thumb = "wait";
            }
            p = new Sprite();
            p.mouseEnabled = false;
            p.mouseChildren = false;
            if(thumb is BitmapData)
            {
               bmp = new Bitmap(BitmapData(thumb),"auto",true);
               bmp.x = 6;
               bmp.y = 6;
               p.addChild(bmp);
            }
            else
            {
               t = cp_label(thumb == "-" ? "Önizleme yok" : "Yükleniyor...",11,CP_DIM);
               t.x = 10;
               t.y = 6;
               p.addChild(t);
            }
            p.graphics.lineStyle(1,FU_EDGE,1,true);
            p.graphics.beginFill(0x1F242B);
            p.graphics.drawRoundRect(0,0,p.width + 12,p.height + 12,10,10);
            p.graphics.endFill();
            p.filters = [new DropShadowFilter(3,90,0,0.5,8,8,1,2)];
            this.stage.addChild(p);
            this.cx_popup = p;
            this.cx_popup_url = url;
         }
         p = this.cx_popup;
         p.x = Math.min(x + 16,this.stage.stageWidth - p.width - 4);
         p.y = y + 18 + p.height > this.stage.stageHeight ? Math.max(4,y - p.height - 8) : y + 18;
      }

      public function cx_preview_line(rest:String) : void
      {
         var sp:int = rest.lastIndexOf(" ");
         var self:TFMProxyLoader = this;
         if(sp < 0)
         {
            return;
         }
         var url:String = rest.substring(0,sp);
         var data:String = rest.substring(sp + 1);
         if(data == "-")
         {
            this.cx_thumbs[url] = "-";
            this.cx_refresh_popup(url);
            return;
         }
         var l:Loader = new Loader();
         l.contentLoaderInfo.addEventListener(Event.COMPLETE,function(e:Event):void
         {
            self.cx_thumbs[url] = Bitmap(l.content).bitmapData;
            self.cx_refresh_popup(url);
         });
         l.loadBytes(gf_base64(data));
      }

      private function cx_refresh_popup(url:String) : void
      {
         var x:Number = 0;
         var y:Number = 0;
         if(this.cx_popup_url == url && this.cx_popup != null)
         {
            x = this.stage.mouseX;
            y = this.stage.mouseY;
            this.cx_hide_preview();
            this.cx_show_preview(url,x,y);
         }
      }

      // ---- search and note panels: a text box at the top ----

      public function cx_input(p:Sprite, w:Number) : TextField
      {
         var self:TFMProxyLoader = this;
         var note:Boolean = this.cp_kind == "note";
         var box:Sprite = new Sprite();
         box.graphics.lineStyle(1,FU_EDGE,1,true);
         box.graphics.beginFill(0x0E1115);
         box.graphics.drawRoundRect(0,0,w,28,8,8);
         box.graphics.endFill();
         box.x = 10;
         box.y = 46;
         p.addChild(box);
         var t:TextField = new TextField();
         t.type = "input";
         t.defaultTextFormat = cp_format(12,CP_TEXT);
         t.x = 8;
         t.y = 5;
         t.width = w - 16;
         t.height = 20;
         t.maxChars = note ? 40 : 100;
         t.text = note ? this.cx_note_text : this.cx_query;
         box.addChild(t);
         t.addEventListener(Event.CHANGE,function(e:Event):void
         {
            if(note)
            {
               self.cx_note_text = t.text;
            }
            else
            {
               self.cx_query = t.text;
            }
         });
         t.addEventListener(KeyboardEvent.KEY_DOWN,function(e:KeyboardEvent):void
         {
            e.stopPropagation();
            if(e.keyCode == 13)
            {
               if(note)
               {
                  self.cs_send("NOTE " + self.cx_note_for + "\t" + t.text);
                  self.cp_close();
               }
               else if(t.text.replace(/\s/g,"") != "")
               {
                  self.cs_send("SEARCH " + t.text);
               }
            }
            else if(e.keyCode == 27)
            {
               self.cp_close();
            }
         });
         t.addEventListener(KeyboardEvent.KEY_UP,function(e:KeyboardEvent):void
         {
            e.stopPropagation();
         });
         return t;
      }

      public function cx_show_results(o:Object) : void
      {
         this.cx_results = o.results as Array || [];
         this.cx_searched = true;
         if(this.cp_kind == "search")
         {
            this.cp_list = null;
            this.cp_refresh();
         }
      }

      public function cx_open_note(name:String) : void
      {
         this.cx_note_for = name;
         this.cx_note_text = this.cx_note(name);
         this.cp_close();
         this.cp_open("note");
      }

      // What the game makes of a "> ..." line (its own quote style).
      private static const CX_QUOTE:RegExp = /<font size='10' color='#6C77C0'><textformat leftmargin='20' rightmargin='20'>(.*?)<\/textformat><\/font>/g;

      private static const CX_QUOTE_NAME:RegExp = /^\s*(@\S+)\s*$/;

      // Discord-like: the name in its normal weight with a few pixels under
      // it, and a quote as a block with a grey bar on its left (drawn, not a
      // character). The card was sized for the game's text, so taller text is
      // used only when it still fits in the card.
      private static const CX_QUOTE_MARGIN:int = 12;

      private var cx_bars:Dictionary = new Dictionary(true);

      private function cx_restyle(tf:TextField, white:String) : void
      {
         var nl:int = white.indexOf("\n");
         if(nl < 0)
         {
            tf.htmlText = white;
            return;
         }
         var head:String = "<textformat leading='3'>" + white.substring(0,nl) + "</textformat>";
         var rest:String = white.substring(nl).replace(CX_QUOTE,function():String
         {
            var line:String = String(arguments[1]);
            var who:Object = CX_QUOTE_NAME.exec(line);
            return "<textformat leftmargin='" + CX_QUOTE_MARGIN + "' rightmargin='12'><font size='11' color='" + (who != null ? "#C4C9D1" : "#9AA1AC") + "'>" + (who != null ? who[1] : line) + "</font></textformat>";
         });
         var oldH:Number = tf.height;
         var room:Number = tf.parent != null ? tf.parent.height - (tf.y + oldH) : 0;
         tf.htmlText = head + rest;
         if(tf.height - oldH > room + 0.5)
         {
            tf.htmlText = white.substring(0,nl) + rest;
            if(tf.height - oldH > room + 0.5)
            {
               tf.htmlText = white;
            }
         }
         this.cx_draw_bars(tf);
      }

      // A rounded grey bar beside every run of quote lines.
      private function cx_draw_bars(tf:TextField) : void
      {
         var old:Shape = this.cx_bars[tf] as Shape;
         var bars:Shape = null;
         var i:int = 0;
         var y:Number = 2;
         var h:Number = 0;
         var top:Number = -1;
         var quote:Boolean = false;
         if(old != null && old.parent != null)
         {
            old.parent.removeChild(old);
         }
         delete this.cx_bars[tf];
         if(tf.parent == null)
         {
            return;
         }
         bars = new Shape();
         for(i = 0; i <= tf.numLines; i++)
         {
            quote = false;
            if(i < tf.numLines)
            {
               h = tf.getLineMetrics(i).height;
               try
               {
                  quote = tf.getLineLength(i) > 0 && int(tf.getTextFormat(tf.getLineOffset(i),tf.getLineOffset(i) + 1).leftMargin) == CX_QUOTE_MARGIN;
               }
               catch(err:Error)
               {
               }
            }
            if(quote && top < 0)
            {
               top = y;
            }
            else if(!quote && top >= 0)
            {
               bars.graphics.beginFill(0x4E5058);
               bars.graphics.drawRoundRect(tf.x + 3,tf.y + top + 1,3,y - top - 2,3,3);
               bars.graphics.endFill();
               top = -1;
            }
            y += h;
         }
         if(bars.height > 0)
         {
            tf.parent.addChildAt(bars,tf.parent.getChildIndex(tf));
            this.cx_bars[tf] = bars;
         }
      }

      // A short two-note chime, made here (no sound file needed).
      public function cx_ding() : void
      {
         var i:int = 0;
         var t:Number = 0;
         var t0:Number = 0;
         var f:Number = 0;
         if(this.cx_chime == null)
         {
            this.cx_chime = new Vector.<Number>();
            for(i = 0; i < 30870; i++)
            {
               t = i / 44100;
               f = t < 0.14 ? 1318.5 : 1760;
               t0 = t < 0.14 ? t : t - 0.14;
               this.cx_chime.push(Math.sin(2 * Math.PI * f * t) * Math.exp(-t0 * 8) * Math.min(1,t0 * 300) * 0.35);
            }
         }
         var chime:Vector.<Number> = this.cx_chime;
         var pos:int = 0;
         var snd:Sound = new Sound();
         snd.addEventListener(SampleDataEvent.SAMPLE_DATA,function(e:SampleDataEvent):void
         {
            var k:int = 0;
            for(k = 0; k < 4096 && pos < chime.length; k++)
            {
               e.data.writeFloat(chime[pos]);
               e.data.writeFloat(chime[pos]);
               pos++;
            }
         });
         snd.play();
      }

      public function cx_notify(name:String) : void
      {
         this.cx_ding();
         this.cp_toast(name + " Café'ye yazdı");
      }

      public function cx_copy(text:String) : void
      {
         try
         {
            Clipboard.generalClipboard.clear();
            Clipboard.generalClipboard.setData(ClipboardFormats.TEXT_FORMAT,text);
         }
         catch(err:Error)
         {
            this.cs_log("clipboard: " + err.message);
         }
      }

      // The Café window as a PNG, sent to the proxy (which saves and uploads it).
      public function cx_shot() : void
      {
         var win:DisplayObjectContainer = this.cp_cafe;
         var r:Rectangle = this.cp_rect;
         if(win == null || win.stage == null || r == null)
         {
            return;
         }
         var toast:Boolean = this.cp_toast_box != null && this.cp_toast_box.visible;
         if(toast)
         {
            this.cp_toast_box.visible = false;
         }
         try
         {
            var bmd:BitmapData = new BitmapData(Math.ceil(r.width),Math.ceil(r.height),false,FU_BG);
            bmd.draw(win,new Matrix(1,0,0,1,-r.x,-r.y),null,null,null,true);
            var png:ByteArray = bmd.encode(bmd.rect,new PNGEncoderOptions(false));
            bmd.dispose();
            this.cs_send("SHOT " + cx_base64(png));
            this.cp_toast("Ekran görüntüsü yükleniyor...");
         }
         catch(err:Error)
         {
            this.cs_log("screenshot failed: " + err.message);
            this.cp_toast("Ekran görüntüsü alınamadı");
         }
         if(toast && this.cp_toast_box != null)
         {
            this.cp_toast_box.visible = true;
         }
      }

      private static function cx_base64(b:ByteArray) : String
      {
         var table:String = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
         var out:Array = [];
         var i:int = 0;
         var n:int = int(b.length);
         var v:int = 0;
         while(i + 2 < n)
         {
            v = b[i] << 16 | b[i + 1] << 8 | b[i + 2];
            out.push(table.charAt(v >> 18 & 63) + table.charAt(v >> 12 & 63) + table.charAt(v >> 6 & 63) + table.charAt(v & 63));
            i += 3;
         }
         if(n - i == 1)
         {
            v = b[i] << 16;
            out.push(table.charAt(v >> 18 & 63) + table.charAt(v >> 12 & 63) + "==");
         }
         else if(n - i == 2)
         {
            v = b[i] << 16 | b[i + 1] << 8;
            out.push(table.charAt(v >> 18 & 63) + table.charAt(v >> 12 & 63) + table.charAt(v >> 6 & 63) + "=");
         }
         return out.join("");
      }

      // ---- search results and favourites, drawn like Café posts ----

      private static const CX_AVATAR_URL:String = "http://avatars.atelier801.com/";

      private var cx_goto_post:int = 0;

      private var cx_goto_at:int = 0;

      private function cx_avatar(id:int, size:Number) : Sprite
      {
         var s:Sprite = new Sprite();
         var mask:Shape = new Shape();
         var l:Loader = null;
         s.graphics.beginFill(0x2A2F36);
         s.graphics.drawRoundRect(0,0,size,size,10,10);
         s.graphics.endFill();
         mask.graphics.beginFill(0);
         mask.graphics.drawRoundRect(0,0,size,size,10,10);
         mask.graphics.endFill();
         s.addChild(mask);
         if(id > 0)
         {
            l = new Loader();
            l.mask = mask;
            l.contentLoaderInfo.addEventListener(Event.COMPLETE,function(e:Event):void
            {
               l.width = size;
               l.height = size;
               if(l.content is Bitmap)
               {
                  Bitmap(l.content).smoothing = true;
               }
            });
            l.contentLoaderInfo.addEventListener(IOErrorEvent.IO_ERROR,function(e:Event):void
            {
            });
            l.load(new URLRequest(CX_AVATAR_URL + id % 10000 + "/" + id + "_50.jpg"));
            s.addChild(l);
         }
         s.mouseEnabled = false;
         s.mouseChildren = false;
         return s;
      }

      // The post's text as the Café shows it: "> " lines as a quote block.
      private static function cx_body_html(text:String) : String
      {
         var lines:Array = text.split(/\r\n|\r|\n/);
         var out:Array = [];
         var i:int = 0;
         var line:String = null;
         var q:String = null;
         var who:Boolean = false;
         for(i = 0; i < lines.length; i++)
         {
            line = String(lines[i]);
            if(line.charAt(0) == ">")
            {
               q = line.substring(1).replace(/^\s+|\s+$/g,"");
               who = /^@\S+$/.test(q);
               out.push("<textformat leftmargin='" + CX_QUOTE_MARGIN + "'><font size='11' color='" + (who ? "#C4C9D1" : "#9AA1AC") + "'>" + cx_escape(q) + "</font></textformat>");
            }
            else if(line.replace(/\s/g,"") == "")
            {
               out.push("<font size='4'> </font>");
            }
            else
            {
               out.push("<font size='12' color='#C9CED6'>" + cx_escape(line) + "</font>");
            }
         }
         return "<font face='Verdana'>" + out.join("\n") + "</font>";
      }

      public function cx_post_card(it:Object, w:Number, fav:Boolean) : Sprite
      {
         var self:TFMProxyLoader = this;
         var row:Sprite = new Sprite();
         var name:String = String(it.author);
         var hash:int = name.indexOf("#");
         var note:String = this.cx_note(name);
         var av:Sprite = this.cx_avatar(int(it.avatar),40);
         av.x = 8;
         av.y = 8;
         row.addChild(av);
         var n:TextField = new TextField();
         n.selectable = false;
         n.mouseEnabled = false;
         n.autoSize = TextFieldAutoSize.LEFT;
         n.htmlText = "<font face='Verdana' size='12' color='#FFFFFF'>" + cx_escape(hash > 0 ? name.substr(0,hash) : name) + "</font><font face='Verdana' size='10' color='#5E6A86'>" + (hash > 0 ? cx_escape(name.substr(hash)) : "") + "</font>" + (note != "" ? "<font face='Verdana' size='10' color='#F2C85B'>  " + cx_escape(note) + "</font>" : "");
         n.x = 56;
         n.y = 7;
         row.addChild(n);
         var when:TextField = cp_label(cp_date(Number(fav ? it.saved_at : it.seen_at)),10,CP_DIM);
         when.x = w - 10 - when.width;
         when.y = 9;
         row.addChild(when);
         var body:TextField = new TextField();
         body.selectable = true;
         body.multiline = true;
         body.wordWrap = true;
         body.width = w - 56 - 12;
         body.autoSize = TextFieldAutoSize.LEFT;
         body.htmlText = cx_body_html(String(it.text));
         body.x = 56;
         body.y = 26;
         row.addChild(body);
         this.cx_draw_bars(body);
         var foot:Number = Math.max(body.y + body.height,av.y + 40) + 6;
         var x:Number = w - 8;
         var btn:Sprite = null;
         if(fav)
         {
            btn = this.cp_text_button("Sil",function():void
            {
               self.cs_send("UNFAV " + int(it.id));
            });
            x -= btn.width;
            btn.x = x;
            btn.y = foot;
            row.addChild(btn);
            x -= 6;
         }
         if(int(it.topic) > 0)
         {
            btn = this.cp_text_button("Mesaja git",function():void
            {
               self.cx_goto(int(it.topic),int(it.post));
            });
            x -= btn.width;
            btn.x = x;
            btn.y = foot;
            row.addChild(btn);
            if(it.title)
            {
               var topic:TextField = cp_label("konu: " + String(it.title).substr(0,50),10,CP_DIM);
               topic.x = 56;
               topic.y = foot + 3;
               row.addChild(topic);
            }
         }
         var h:Number = foot + (btn != null ? 28 : 0);
         row.graphics.beginFill(CP_CARD);
         row.graphics.drawRoundRect(0,0,w,h,10,10);
         row.graphics.endFill();
         return row;
      }

      // ---- "Mesaja git": open the topic, then scroll to the post ----

      public function cx_goto(topic:int, post:int) : void
      {
         this.cs_send("GOTO " + topic);
         this.cx_goto_post = post;
         this.cx_goto_at = getTimer();
         this.cp_close();
      }

      private static function cx_has_int(o:Object, value:int) : Boolean
      {
         var v:XML = null;
         try
         {
            for each(v in describeType(o).elements("variable"))
            {
               if(String(v.attribute("type")) == "int" && int(o[String(v.attribute("name"))]) == value)
               {
                  return true;
               }
            }
         }
         catch(err:Error)
         {
         }
         return false;
      }

      private function cx_try_goto() : void
      {
         var card:* = undefined;
         if(getTimer() - this.cx_goto_at > 6000)
         {
            this.cx_goto_post = 0;
            this.cp_toast("Mesaj bu konuda bulunamadı");
            return;
         }
         for(card in this.cx_cards)
         {
            if(card.stage != null && cx_has_int(card,this.cx_goto_post))
            {
               this.cx_goto_post = 0;
               this.cx_scroll_to(DisplayObject(card));
               return;
            }
         }
      }

      // The post list's own "scroll to" (Boolean, position), found by its shape.
      private function cx_scroll_to(card:DisplayObject) : void
      {
         var d:DisplayObjectContainer = card.parent;
         var depth:int = 0;
         var m:XML = null;
         var x:XML = null;
         var p:XMLList = null;
         var t:String = null;
         while(d != null && depth < 6)
         {
            try
            {
               x = describeType(d);
               for each(m in x.elements("method"))
               {
                  p = m.elements("parameter");
                  t = p.length() == 2 ? String(p[1].attribute("type")) : "";
                  if(String(m.attribute("declaredBy")) == String(x.attribute("name")) && p.length() == 2 && String(p[0].attribute("type")) == "Boolean" && (t == "int" || t == "Number") && String(m.attribute("returnType")) == "void")
                  {
                     this.cs_log("goto: scrolling with " + String(m.attribute("name")) + " at depth " + depth);
                     d[String(m.attribute("name"))](false,-card.y);
                     this.cx_flash(card);
                     return;
                  }
               }
            }
            catch(err:Error)
            {
               this.cs_log("goto: scroll failed: " + err.message);
            }
            d = d.parent;
            depth++;
         }
         this.cs_log("goto: no scroll method found");
         this.cx_flash(card);
      }

      // A short blue glow over the post we went to.
      private function cx_flash(card:DisplayObject) : void
      {
         var c:DisplayObjectContainer = card as DisplayObjectContainer;
         if(c == null)
         {
            return;
         }
         var b:Rectangle = c.getBounds(c);
         var s:Shape = new Shape();
         var start:int = getTimer();
         s.graphics.beginFill(0x5865F2,0.35);
         s.graphics.drawRect(0,0,b.right,b.bottom);
         s.graphics.endFill();
         c.addChild(s);
         s.addEventListener(Event.ENTER_FRAME,function(e:Event):void
         {
            var k:Number = (getTimer() - start) / 1800;
            s.alpha = 1 - k;
            if(k >= 1)
            {
               s.removeEventListener(Event.ENTER_FRAME,arguments.callee);
               if(s.parent != null)
               {
                  s.parent.removeChild(s);
               }
            }
         });
      }
