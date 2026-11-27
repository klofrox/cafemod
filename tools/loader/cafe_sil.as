
      // ---- Cafe "Sil": hide a player's Cafe posts (filtered by the local proxy) ----

      private static const CS_PORT:int = 11810;

      private static const CS_NAME:RegExp = /^[^#\s<>]{1,40}#\d{4}$/;

      private var cs_author:String = null;

      private var cs_author_at:int = 0;

      private var cs_post_text:String = "";

      private var cs_found_text:String = "";

      private var cs_done:Dictionary = new Dictionary(true);

      private var cs_sock:Socket = null;

      private var cs_queue:Array = [];

      public static var cs_instance:TFMProxyLoader = null;

      public static function cs_static_log(s:String) : void
      {
         if(cs_instance != null)
         {
            cs_instance.cs_log(s);
         }
      }

      private function cs_init() : void
      {
         var self:TFMProxyLoader = this;
         cs_instance = this;
         this.loaderInfo.uncaughtErrorEvents.addEventListener("uncaughtError",function(e:*):void
         {
            var err:* = e.error;
            if(err is Error)
            {
               self.cs_log("uncaught error #" + Error(err).errorID + ": " + Error(err).message + " | " + Error(err).getStackTrace());
            }
            else
            {
               self.cs_log("uncaught: " + String(err));
            }
         });
         this.stage.addEventListener(MouseEvent.MOUSE_DOWN,this.cs_on_down,true,0,true);
         this.stage.addEventListener(Event.ADDED,this.cs_on_added,true,0,true);
         this.cx_start();
         this.cs_log("ready");
      }

      private function cs_on_down(e:MouseEvent) : void
      {
         var d:DisplayObject = e.target as DisplayObject;
         var depth:int = 0;
         var found:String = null;
         while(d != null && depth < 10 && found == null)
         {
            found = this.cs_author_in(d);
            d = d.parent;
            depth++;
         }
         if(found != null)
         {
            if(found != this.cs_author)
            {
               this.cs_log("clicked post of " + found);
            }
            this.cs_author = found;
            this.cs_author_at = getTimer();
            this.cs_post_text = this.cs_found_text;
         }
      }

      private function cs_author_in(obj:Object) : String
      {
         var x:XML = null;
         var v:XML = null;
         var t:String = null;
         var val:* = undefined;
         var w:XML = null;
         var s:* = undefined;
         try
         {
            x = describeType(obj);
         }
         catch(err:Error)
         {
            return null;
         }
         for each(v in x.elements("variable"))
         {
            t = String(v.attribute("type"));
            if(t == "String" || t == "int" || t == "uint" || t == "Number" || t == "Boolean" || t.indexOf("flash.") == 0 || t.indexOf("__AS3__") == 0)
            {
               continue;
            }
            try
            {
               val = obj[String(v.attribute("name"))];
               if(val == null)
               {
                  continue;
               }
               for each(w in describeType(val).elements("variable"))
               {
                  if(String(w.attribute("type")) == "String")
                  {
                     s = val[String(w.attribute("name"))];
                     if(s is String && CS_NAME.test(s))
                     {
                        this.cs_found_text = cs_longest_other(val,describeType(val),s);
                        return s;
                     }
                  }
               }
            }
            catch(err2:Error)
            {
            }
         }
         return null;
      }

      // The message itself: the longest other text of the post's data.
      private static function cs_longest_other(val:Object, x:XML, author:String) : String
      {
         var w:XML = null;
         var s:* = undefined;
         var best:String = "";
         for each(w in x.elements("variable"))
         {
            if(String(w.attribute("type")) == "String")
            {
               try
               {
                  s = val[String(w.attribute("name"))];
               }
               catch(err:Error)
               {
                  continue;
               }
               if(s is String && s != author && String(s).length > best.length)
               {
                  best = s;
               }
            }
         }
         return best;
      }

      private var cs_tree_done:Object = {};

      private var cs_tree_count:int = 0;

      private function cs_dump_tree(root:DisplayObjectContainer) : void
      {
         var lines:Array = [];
         this.cs_dump_node(root,0,lines);
         this.cs_log("tree of " + getQualifiedClassName(root) + " (" + int(root.width) + "x" + int(root.height) + "):\n" + lines.join("\n"));
      }

      private function cs_dump_node(d:DisplayObject, depth:int, lines:Array) : void
      {
         var c:DisplayObjectContainer = d as DisplayObjectContainer;
         var i:int = 0;
         if(lines.length >= 120)
         {
            return;
         }
         var name:String = getQualifiedClassName(d);
         if(name.charAt(0) == "§" || name.indexOf("\\x") != -1)
         {
            name = "<obf>";
         }
         lines.push("LOG    " + new Array(depth + 1).join("  ") + name + " @" + int(d.x) + "," + int(d.y) + " " + int(d.width) + "x" + int(d.height) + (c != null ? " [" + c.numChildren + "]" : "") + (d.visible ? "" : " hidden"));
         if(c == null || depth >= 5)
         {
            return;
         }
         for(i = 0; i < c.numChildren; i++)
         {
            this.cs_dump_node(c.getChildAt(i),depth + 1,lines);
         }
      }

      private var cs_asset_names:Object = {};

      private var cs_asset_count:int = 0;

      private function cs_on_added(e:Event) : void
      {
         var t:Object = e.target;
         if(t is DisplayObject)
         {
            try
            {
               this.fu_scan(DisplayObject(t),4);
               // Big windows fill in their parts a moment later: look again.
               if(t is DisplayObjectContainer && t.width >= 300 && t.height >= 150)
               {
                  setTimeout(this.fu_rescan,600,t);
               }
            }
            catch(fuErr:Error)
            {
               this.cs_log("flat ui failed: " + fuErr.message);
            }
         }
         if(this.cs_done[t] || this.cs_author == null || getTimer() - this.cs_author_at > 2000)
         {
            return;
         }
         var info:Object = this.cs_menu_info(t);
         if(info == null)
         {
            return;
         }
         this.cs_done[t] = true;
         var author:String = this.cs_author;
         var text:String = this.cs_post_text;
         setTimeout(this.cs_patch,1,t,info,author,text);
      }

      private function cs_menu_info(t:Object) : Object
      {
         var x:XML = null;
         var m:XML = null;
         var v:XML = null;
         var p:XMLList = null;
         try
         {
            x = describeType(t);
         }
         catch(err:Error)
         {
            return null;
         }
         var cls:String = String(x.attribute("name"));
         var add:String = null;
         var voids:Array = [];
         var flag:String = null;
         var create:String = null;
         var rows:String = null;
         for each(m in x.elements("method"))
         {
            if(String(m.attribute("declaredBy")) != cls)
            {
               continue;
            }
            p = m.elements("parameter");
            if(p.length() >= 5 && String(p[0].attribute("type")) == "String" && String(p[1].attribute("type")) == "Function")
            {
               if(String(m.attribute("returnType")) == cls)
               {
                  add = String(m.attribute("name"));
               }
               else
               {
                  create = String(m.attribute("name"));
               }
            }
            if(p.length() == 0 && String(m.attribute("returnType")) == "void")
            {
               voids.push(String(m.attribute("name")));
            }
         }
         // The "lay out on next show" flag is the menu's own Boolean, not one
         // inherited from its base class.
         var inherited:Object = {};
         var sup:XML = null;
         try
         {
            sup = describeType(t.loaderInfo.applicationDomain.getDefinition(String(x.elements("extendsClass")[0].attribute("type"))));
            for each(v in sup.elements("factory").elements("variable"))
            {
               inherited[String(v.attribute("name"))] = true;
            }
         }
         catch(err3:Error)
         {
         }
         for each(v in x.elements("variable"))
         {
            if(String(v.attribute("type")) == "Boolean" && !inherited[String(v.attribute("name"))])
            {
               flag = String(v.attribute("name"));
            }
            if(String(v.attribute("type")).indexOf("Vector") != -1 && !inherited[String(v.attribute("name"))])
            {
               rows = String(v.attribute("name"));
            }
         }
         if(add == null || create == null || rows == null)
         {
            return null;
         }
         return {"add":add,"voids":voids,"flag":flag,"create":create,"rows":rows};
      }

      private function cs_patch(menu:Object, info:Object, author:String, text:String) : void
      {
         var self:TFMProxyLoader = this;
         try
         {
            var rows:* = menu[info.rows];
            var n:int = int(rows.length);
            if(n < 2)
            {
               this.cs_log("menu has " + n + " rows, not adding Sil");
               return;
            }
            var last:DisplayObject = rows[n - 1] as DisplayObject;
            var above:DisplayObject = rows[n - 2] as DisplayObject;
            var step:Number = last.y - above.y;
            if(last.parent == null || last.parent == menu || step <= 0)
            {
               this.cs_log("unexpected menu layout (step " + step + "), not adding Sil");
               return;
            }
            // The menu's own row builder: same text style, hover and click.
            var items:Array = [["Favori",function():void
            {
               self.cs_send("FAV " + author + "\t" + text.replace(/[\r\n\t]+/g," "));
            }],["PP indir",function():void
            {
               self.cs_send("PP " + author);
            }],["Bildirim",function():void
            {
               self.cs_send("WATCH " + author);
            }],["Not",function():void
            {
               self.cx_open_note(author);
            }],["Sil",function():void
            {
               self.cs_send("BLOCK " + author);
            }]];
            var bg:DisplayObject = menu.getChildAt(0);
            var frame:DisplayObject = menu.getChildAt(menu.numChildren - 1);
            var k:int = 0;
            var row:* = null;
            for(k = 0; k < items.length; k++)
            {
               row = menu[info.create](items[k][0],items[k][1]);
               // Rows alternate two colours: the row two above has ours.
               row.graphics.copyFrom(rows[rows.length - 2]["graphics"]);
               row.x = last.x;
               row.y = last.y + step;
               last.parent.addChildAt(row,last.parent.getChildIndex(last) + 1);
               rows.push(row);
               last = row;
               // Background (bottom) and frame (top) grow by one row.
               bg.height += step;
               frame.height += step;
            }
            // Keep it on screen.
            if(menu.stage != null && menu.y + menu.height > menu.stage.stageHeight)
            {
               menu.y = menu.stage.stageHeight - menu.height;
            }
            this.cs_log("menu rows added for " + author + " (" + n + " rows, step " + step + ")");
         }
         catch(err:Error)
         {
            this.cs_log("patch failed: " + err.message);
         }
      }

      public function cs_log(s:String) : void
      {
         this.cs_send("LOG " + s);
      }

      public function cs_send(line:String) : void
      {
         var self:TFMProxyLoader = this;
         this.cs_queue.push(line);
         if(this.cs_sock != null)
         {
            if(this.cs_sock.connected)
            {
               this.cs_flush();
            }
            return;
         }
         this.cs_sock = new Socket();
         this.cs_sock.addEventListener(Event.CONNECT,function(e:Event):void
         {
            self.cs_queue.unshift("LIST");
            self.cs_flush();
         });
         this.cs_sock.addEventListener(ProgressEvent.SOCKET_DATA,function(e:Event):void
         {
            self.cs_read();
         });
         this.cs_sock.addEventListener(IOErrorEvent.IO_ERROR,function(e:Event):void
         {
            self.cs_reset();
         });
         this.cs_sock.addEventListener(SecurityErrorEvent.SECURITY_ERROR,function(e:Event):void
         {
            self.cs_reset();
         });
         this.cs_sock.addEventListener(Event.CLOSE,function(e:Event):void
         {
            self.cs_reset();
         });
         this.cs_sock.connect("127.0.0.1",CS_PORT);
      }

      private var cs_inbox:String = "";

      public function cs_read() : void
      {
         var i:int = 0;
         var line:String = null;
         this.cs_inbox += this.cs_sock.readUTFBytes(this.cs_sock.bytesAvailable);
         while((i = this.cs_inbox.indexOf("\n")) != -1)
         {
            line = this.cs_inbox.substring(0,i);
            this.cs_inbox = this.cs_inbox.substring(i + 1);
            if(line.indexOf("STATE ") == 0)
            {
               try
               {
                  this.cp_state = getDefinitionByName("JSON").parse(line.substring(6));
                  this.cx_ver++;
                  this.cp_refresh();
                  if(this.cp_trash_draw != null)
                  {
                     this.cp_trash_draw();
                  }
               }
               catch(err:Error)
               {
                  this.cs_log("bad state: " + err.message);
               }
            }
            else if(line.indexOf("GIF ") == 0)
            {
               try
               {
                  this.gf_add(line);
               }
               catch(gifErr:Error)
               {
                  this.cs_log("bad gif: " + gifErr.message);
               }
            }
            else if(line.indexOf("TOAST ") == 0)
            {
               this.cp_toast(line.substring(6));
            }
            else if(line.indexOf("NOTIFY ") == 0)
            {
               this.cx_notify(line.substring(7));
            }
            else if(line.indexOf("LINK ") == 0)
            {
               this.cx_copy(line.substring(5));
            }
            else if(line.indexOf("MENTION ") == 0)
            {
               this.cx_mention(line.substring(8));
            }
            else if(line.indexOf("RESULTS ") == 0)
            {
               try
               {
                  this.cx_show_results(getDefinitionByName("JSON").parse(line.substring(8)));
               }
               catch(resErr:Error)
               {
                  this.cs_log("bad results: " + resErr.message);
               }
            }
            else if(line.indexOf("AVATARS ") == 0)
            {
               this.av_refresh(line);
            }
            else if(line.indexOf("PREVIEW ") == 0)
            {
               this.cx_preview_line(line.substring(8));
            }
         }
      }

      public function cs_reset() : void
      {
         this.cs_sock = null;
      }

      public function cs_flush() : void
      {
         while(this.cs_queue.length > 0)
         {
            this.cs_sock.writeUTFBytes(String(this.cs_queue.shift()) + "\n");
         }
         this.cs_sock.flush();
      }
