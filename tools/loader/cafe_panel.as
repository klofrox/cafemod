
      // ---- Café panel: title buttons, blocked players, favourites, toasts ----
      //
      // The state (blocked names, favourite messages) lives in the proxy; it
      // sends "STATE <json>" after every change and the panel redraws from it.

      private static const CP_TEXT:uint = 0xC9CED6;

      private static const CP_DIM:uint = 0x7D8590;

      private static const CP_NAME:uint = 0x98A6FF;

      private static const CP_CARD:uint = 0x171A1F;

      private static const CP_HOVER:uint = 0x323844;

      public var cp_state:Object = {"blocked":[],"favs":[],"watched":[]};

      public function cx_watched(name:String) : Boolean
      {
         var w:Array = this.cp_state.watched as Array;
         var i:int = 0;
         for(i = 0; w != null && i < w.length; i++)
         {
            if(String(w[i]).toLowerCase() == name.toLowerCase())
            {
               return true;
            }
         }
         return false;
      }

      private var cp_icons:Dictionary = new Dictionary(true);

      private var cp_cafe:DisplayObjectContainer = null;

      private var cp_rect:Rectangle = null;

      private var cp_panel:Sprite = null;

      private var cp_kind:String = null;

      private var cp_list:Sprite = null;

      private var cp_view_h:Number = 0;

      private var cp_toast_box:Sprite = null;

      private static function cp_format(size:int, colour:uint, bold:Boolean = false) : TextFormat
      {
         return new TextFormat("Verdana",size,colour,bold);
      }

      private static function cp_label(text:String, size:int, colour:uint, width:Number = 0, bold:Boolean = false) : TextField
      {
         var t:TextField = new TextField();
         t.defaultTextFormat = cp_format(size,colour,bold);
         t.selectable = false;
         t.mouseEnabled = false;
         if(width > 0)
         {
            t.width = width;
            t.wordWrap = true;
            t.multiline = true;
         }
         t.autoSize = TextFieldAutoSize.LEFT;
         t.text = text;
         return t;
      }

      // A flat square button with a drawn icon ("refresh", "close", "star", "block").
      private static function cp_draw_icon(g:Graphics, kind:String, size:Number, bg:uint) : void
      {
         var c:Number = size / 2;
         var r:Number = size * 0.28;
         var a:Number = 0;
         var i:int = 0;
         g.clear();
         g.lineStyle(1,FU_EDGE,1,true);
         g.beginFill(bg);
         g.drawRoundRect(0,0,size,size,7,7);
         g.endFill();
         g.lineStyle(2,CP_TEXT,1,true,"normal","round","round");
         if(kind == "close")
         {
            g.moveTo(c - r,c - r);
            g.lineTo(c + r,c + r);
            g.moveTo(c + r,c - r);
            g.lineTo(c - r,c + r);
         }
         else if(kind == "refresh")
         {
            // An open circle with an arrow head at its end.
            for(i = 0; i <= 12; i++)
            {
               a = -Math.PI * 0.35 + i / 12 * Math.PI * 1.55;
               if(i == 0)
               {
                  g.moveTo(c + Math.cos(a) * r,c + Math.sin(a) * r);
               }
               else
               {
                  g.lineTo(c + Math.cos(a) * r,c + Math.sin(a) * r);
               }
            }
            a = -Math.PI * 0.35;
            g.moveTo(c + Math.cos(a) * r,c + Math.sin(a) * r);
            g.lineTo(c + Math.cos(a) * r + 3.5,c + Math.sin(a) * r - 1);
            g.moveTo(c + Math.cos(a) * r,c + Math.sin(a) * r);
            g.lineTo(c + Math.cos(a) * r + 0.5,c + Math.sin(a) * r - 4);
         }
         else if(kind == "star")
         {
            g.lineStyle(1.5,0xF2C85B,1,true);
            g.beginFill(0xF2C85B);
            for(i = 0; i <= 10; i++)
            {
               a = -Math.PI / 2 + i * Math.PI / 5;
               var rr:Number = i % 2 == 0 ? r * 1.25 : r * 0.5;
               if(i == 0)
               {
                  g.moveTo(c + Math.cos(a) * rr,c + Math.sin(a) * rr);
               }
               else
               {
                  g.lineTo(c + Math.cos(a) * rr,c + Math.sin(a) * rr);
               }
            }
            g.endFill();
         }
         else if(kind == "camera")
         {
            g.drawRoundRect(c - r * 1.25,c - r * 0.65,r * 2.5,r * 1.75,4,4);
            g.drawCircle(c,c + r * 0.2,r * 0.5);
            g.moveTo(c - r * 0.5,c - r * 0.65);
            g.lineTo(c - r * 0.3,c - r * 1.05);
            g.lineTo(c + r * 0.3,c - r * 1.05);
            g.lineTo(c + r * 0.5,c - r * 0.65);
         }
         else if(kind == "search")
         {
            g.drawCircle(c - r * 0.2,c - r * 0.2,r * 0.75);
            g.moveTo(c + r * 0.35,c + r * 0.35);
            g.lineTo(c + r * 1.05,c + r * 1.05);
         }
         else if(kind == "bell")
         {
            g.moveTo(c - r * 1.05,c + r * 0.7);
            g.curveTo(c - r * 0.75,c + r * 0.35,c - r * 0.75,c - r * 0.1);
            g.curveTo(c - r * 0.75,c - r * 1.05,c,c - r * 1.05);
            g.curveTo(c + r * 0.75,c - r * 1.05,c + r * 0.75,c - r * 0.1);
            g.curveTo(c + r * 0.75,c + r * 0.35,c + r * 1.05,c + r * 0.7);
            g.lineTo(c - r * 1.05,c + r * 0.7);
            g.moveTo(c - r * 0.3,c + r * 1.05);
            g.lineTo(c + r * 0.3,c + r * 1.05);
         }
         else if(kind == "block")
         {
            g.lineStyle(2,0xE0676B,1,true);
            g.drawCircle(c,c,r * 1.1);
            g.moveTo(c - r * 0.78,c + r * 0.78);
            g.lineTo(c + r * 0.78,c - r * 0.78);
         }
      }

      // The game's own refresh/close images stay (invisible, still clickable);
      // our flat icon is drawn on top of them, ignoring the mouse.
      private function cp_restyle(asset:DisplayObject, kind:String) : void
      {
         var parent:DisplayObjectContainer = asset.parent;
         asset.alpha = 0;
         if(parent == null || this.cp_icons[parent])
         {
            return;
         }
         var b:Rectangle = asset.getBounds(parent);
         var size:Number = Math.min(22,Math.max(b.width,b.height));
         var icon:Sprite = new Sprite();
         cp_draw_icon(icon.graphics,kind,size,FU_BUTTON);
         icon.x = b.x + (b.width - size) / 2;
         icon.y = b.y + (b.height - size) / 2;
         icon.mouseEnabled = false;
         icon.mouseChildren = false;
         parent.addChild(icon);
         this.cp_icons[parent] = icon;
         var hit:InteractiveObject = asset as InteractiveObject;
         if(hit == null)
         {
            hit = parent as InteractiveObject;
         }
         if(hit != null)
         {
            hit.addEventListener(MouseEvent.ROLL_OVER,function(e:Event):void
            {
               cp_draw_icon(icon.graphics,kind,size,CP_HOVER);
            });
            hit.addEventListener(MouseEvent.ROLL_OUT,function(e:Event):void
            {
               cp_draw_icon(icon.graphics,kind,size,FU_BUTTON);
            });
         }
      }

      // Our own flat button.
      private function cp_button(kind:String, size:Number, onClick:Function) : Sprite
      {
         var b:Sprite = new Sprite();
         cp_draw_icon(b.graphics,kind,size,FU_BUTTON);
         b.buttonMode = true;
         b.useHandCursor = true;
         b.addEventListener(MouseEvent.ROLL_OVER,function(e:Event):void
         {
            cp_draw_icon(b.graphics,kind,size,CP_HOVER);
         });
         b.addEventListener(MouseEvent.ROLL_OUT,function(e:Event):void
         {
            cp_draw_icon(b.graphics,kind,size,FU_BUTTON);
         });
         b.addEventListener(MouseEvent.CLICK,function(e:MouseEvent):void
         {
            e.stopPropagation();
            onClick();
         });
         return b;
      }

      private function cp_text_button(text:String, onClick:Function) : Sprite
      {
         var b:Sprite = new Sprite();
         var t:TextField = cp_label(text,11,CP_TEXT);
         var draw:Function = function(bg:uint):void
         {
            b.graphics.clear();
            b.graphics.lineStyle(1,FU_EDGE,1,true);
            b.graphics.beginFill(bg);
            b.graphics.drawRoundRect(0,0,t.width + 16,20,8,8);
            b.graphics.endFill();
         };
         t.x = 8;
         t.y = 1;
         b.addChild(t);
         draw(FU_BUTTON);
         b.buttonMode = true;
         b.mouseChildren = false;
         b.addEventListener(MouseEvent.ROLL_OVER,function(e:Event):void
         {
            draw(CP_HOVER);
         });
         b.addEventListener(MouseEvent.ROLL_OUT,function(e:Event):void
         {
            draw(FU_BUTTON);
         });
         b.addEventListener(MouseEvent.CLICK,function(e:MouseEvent):void
         {
            e.stopPropagation();
            onClick();
         });
         return b;
      }

      // The Café window: its refresh button sits in the title bar.
      private function cp_setup_cafe(refresh:DisplayObject) : void
      {
         var win:DisplayObjectContainer = refresh.parent;
         var self:TFMProxyLoader = this;
         if(win == null || win == this.cp_cafe)
         {
            return;
         }
         this.cp_cafe = win;
         this.cp_panel = null;
         var r:Rectangle = this.fu_rects[win] as Rectangle;
         this.cp_rect = r != null ? r : new Rectangle(-8,-36,776,364);
         var b:Rectangle = refresh.getBounds(win);
         var block:Sprite = this.cp_button("block",22,function():void
         {
            self.cp_open("blocked");
         });
         var star:Sprite = this.cp_button("star",22,function():void
         {
            self.cp_open("favs");
         });
         var shot:Sprite = this.cp_button("camera",22,function():void
         {
            self.cx_shot();
         });
         var bell:Sprite = this.cp_button("bell",22,function():void
         {
            self.cp_open("watched");
         });
         var find:Sprite = this.cp_button("search",22,function():void
         {
            self.cp_open("search");
         });
         block.x = b.x - 28;
         star.x = b.x - 56;
         shot.x = b.x - 84;
         bell.x = b.x - 112;
         find.x = b.x - 140;
         block.y = star.y = shot.y = bell.y = find.y = b.y + (b.height - 22) / 2;
         win.addChild(find);
         win.addChild(block);
         win.addChild(star);
         win.addChild(shot);
         win.addChild(bell);
         this.cs_send("LIST");
      }

      public function cp_open(kind:String) : void
      {
         if(this.cp_panel != null && this.cp_kind == kind)
         {
            this.cp_close();
            return;
         }
         this.cp_kind = kind;
         this.cp_refresh();
      }

      public function cp_close() : void
      {
         if(this.cp_panel != null && this.cp_panel.parent != null)
         {
            this.cp_panel.parent.removeChild(this.cp_panel);
         }
         this.cp_panel = null;
         this.cp_kind = null;
      }

      private static function cp_date(seconds:Number) : String
      {
         var d:Date = new Date(seconds * 1000);
         var two:Function = function(n:int):String
         {
            return n < 10 ? "0" + n : String(n);
         };
         return two(d.date) + "." + two(d.month + 1) + "." + d.fullYear + " " + two(d.hours) + ":" + two(d.minutes);
      }

      // (Re)draw the open panel from cp_state.
      public function cp_refresh() : void
      {
         var self:TFMProxyLoader = this;
         var win:DisplayObjectContainer = this.cp_cafe;
         var i:int = 0;
         var y:Number = 0;
         var row:Sprite = null;
         var t:TextField = null;
         var btn:Sprite = null;
         if(this.cp_kind == null || win == null || win.stage == null)
         {
            return;
         }
         var oldScroll:Number = this.cp_list != null ? this.cp_list.y : 0;
         if(this.cp_panel != null && this.cp_panel.parent != null)
         {
            this.cp_panel.parent.removeChild(this.cp_panel);
         }
         var r:Rectangle = new Rectangle(this.cp_rect.x + 10,this.cp_rect.y + 36,this.cp_rect.width - 20,this.cp_rect.height - 46);
         var p:Sprite = new Sprite();
         p.x = r.x;
         p.y = r.y;
         p.graphics.lineStyle(1,FU_EDGE,1,true);
         p.graphics.beginFill(FU_BG);
         p.graphics.drawRoundRect(0,0,r.width,r.height,12,12);
         p.graphics.endFill();
         // Swallow clicks so the Café under the panel stays untouched.
         p.addEventListener(MouseEvent.MOUSE_DOWN,function(e:MouseEvent):void
         {
            e.stopPropagation();
         });
         var typing:Boolean = this.cp_kind == "search" || this.cp_kind == "note";
         var items:Array = this.cp_kind == "search" ? this.cx_results : (this.cp_kind == "note" ? [] : this.cp_state[this.cp_kind] as Array);
         if(items == null)
         {
            items = [];
         }
         var watched:Boolean = this.cp_kind == "watched";
         var title:TextField = cp_label(this.cp_kind == "note" ? "Not: " + this.cx_note_for : (this.cp_kind == "search" ? "Café arşivinde ara" : (this.cp_kind == "favs" ? "Favori mesajlar" : (watched ? "Bildirimi açık oyuncular" : "Engellenen oyuncular"))) + "  (" + items.length + ")",13,CP_TEXT,0,true);
         if(this.cp_kind == "note")
         {
            title.text = "Not: " + this.cx_note_for;
         }
         title.x = 14;
         title.y = 9;
         p.addChild(title);
         var close:Sprite = this.cp_button("close",20,function():void
         {
            self.cp_close();
         });
         close.x = r.width - 30;
         close.y = 8;
         p.addChild(close);
         p.graphics.lineStyle(1,FU_EDGE,1,true);
         p.graphics.moveTo(1,36);
         p.graphics.lineTo(r.width - 1,36);

         // The scrolling list, clipped to the panel.
         var view:Sprite = new Sprite();
         view.x = 10;
         view.y = typing ? 84 : 44;
         this.cp_view_h = r.height - view.y - 10;
         var mask:Shape = new Shape();
         mask.graphics.beginFill(0);
         mask.graphics.drawRect(0,0,r.width - 20,this.cp_view_h);
         mask.graphics.endFill();
         view.addChild(mask);
         var list:Sprite = new Sprite();
         list.mask = mask;
         view.addChild(list);
         p.addChild(view);
         this.cp_list = list;
         var w:Number = r.width - 20;
         var input:TextField = typing ? this.cx_input(p,w) : null;
         if(typing && items.length == 0)
         {
            t = cp_label(this.cp_kind == "note" ? "Sadece sen görürsün; ismin yanında çıkar. Yaz, Enter'a bas. Boş bırakıp Enter: not silinir." : (this.cx_searched ? "Bulunamadı." : "Kelime yaz ve Enter'a bas. @isim yazarsan o kişinin mesajlarını arar (ör. @Eby çay). Gördüğün her mesaj arşivde."),12,CP_DIM,w - 20);
            t.x = 6;
            t.y = 6;
            list.addChild(t);
         }
         else if(items.length == 0)
         {
            t = cp_label(this.cp_kind == "favs" ? "Henüz favori yok. Bir mesajın menüsünden \"Favori\" seç." : (watched ? "Kimse yok. Bir mesajın menüsünden \"Bildirim\" seç; o oyuncu Café'ye yazınca ses gelir." : "Engellenen oyuncu yok. Bir mesajın menüsünden \"Sil\" seç."),12,CP_DIM,w - 20);
            t.x = 6;
            t.y = 6;
            list.addChild(t);
         }
         for(i = 0; i < items.length; i++)
         {
            row = new Sprite();
            btn = null;
            if(this.cp_kind == "search" || this.cp_kind == "favs")
            {
               // Drawn like a Café post: avatar, name, text, quotes.
               row = this.cx_post_card(items[i],w,this.cp_kind == "favs");
               row.y = y;
               list.addChild(row);
               y += row.height + 6;
               continue;
            }
            {
               row.addChild(t = cp_label(String(items[i]),12,CP_TEXT,0,true));
               t.x = 10;
               t.y = 8;
               btn = this.cp_text_button(watched ? "Kapat" : "Kaldır",(function(name:String, command:String):Function
               {
                  return function():void
                  {
                     self.cs_send(command + name);
                  };
               })(String(items[i]),watched ? "UNWATCH " : "UNBLOCK "));
               var h:Number = 34;
            }
            row.graphics.beginFill(CP_CARD);
            row.graphics.drawRoundRect(0,0,w,h,10,10);
            row.graphics.endFill();
            if(btn != null)
            {
               btn.x = w - btn.width - 8;
               btn.y = (h - 20) / 2;
               row.addChild(btn);
            }
            row.y = y;
            list.addChild(row);
            y += h + 6;
         }
         var maxScroll:Number = Math.max(0,list.height - this.cp_view_h);
         list.y = Math.max(-maxScroll,Math.min(0,oldScroll));
         p.addEventListener(MouseEvent.MOUSE_WHEEL,function(e:MouseEvent):void
         {
            list.y = Math.max(-maxScroll,Math.min(0,list.y + e.delta * 12));
            e.stopPropagation();
         });
         win.addChild(p);
         this.cp_panel = p;
         if(input != null && win.stage != null)
         {
            win.stage.focus = input;
            input.setSelection(input.length,input.length);
         }
      }

      public function cp_toast(text:String) : void
      {
         var host:DisplayObjectContainer = this.cp_cafe != null && this.cp_cafe.stage != null ? this.cp_cafe : this.stage;
         var self:TFMProxyLoader = this;
         if(this.cp_toast_box != null && this.cp_toast_box.parent != null)
         {
            this.cp_toast_box.parent.removeChild(this.cp_toast_box);
         }
         var box:Sprite = new Sprite();
         var t:TextField = cp_label(text,12,CP_TEXT);
         t.x = 12;
         t.y = 6;
         box.addChild(t);
         box.graphics.lineStyle(1,FU_EDGE,1,true);
         box.graphics.beginFill(0x1F242B);
         box.graphics.drawRoundRect(0,0,t.width + 24,t.height + 12,10,10);
         box.graphics.endFill();
         box.mouseEnabled = false;
         box.mouseChildren = false;
         box.filters = [new DropShadowFilter(3,90,0,0.5,8,8,1,2)];
         if(host == this.cp_cafe && this.cp_rect != null)
         {
            box.x = this.cp_rect.x + (this.cp_rect.width - box.width) / 2;
            box.y = this.cp_rect.y + this.cp_rect.height - box.height - 14;
         }
         else
         {
            box.x = (this.stage.stageWidth - box.width) / 2;
            box.y = 40;
         }
         host.addChild(box);
         this.cp_toast_box = box;
         setTimeout(function():void
         {
            if(box.parent != null)
            {
               box.parent.removeChild(box);
            }
         },2600);
      }
