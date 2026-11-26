
      // ---- Dark theme: recolour the game's UI palette ----
      //
      // The game keeps its UI colours (Café, menus, panels, lists) as int
      // fields of a palette object reached from a static field. Once the game
      // code is loaded, look through the static fields (and one level below)
      // for objects that look like a palette and turn their dark teal colours
      // into neutral dark greys. Windows drawn afterwards use the new colours.

      private static const TH_MAX_FRAMES:int = 24 * 90;

      private var th_slots:Array = null;

      private var th_seen:Dictionary = new Dictionary(true);

      private var th_frames:int = 0;

      private var th_found:int = 0;

      public static function cs_static_game(domain:ApplicationDomain) : void
      {
         if(cs_instance != null)
         {
            cs_instance.th_start(domain);
         }
      }

      private static function th_skip_type(t:String) : Boolean
      {
         return t.indexOf("::") != -1 || t == "String" || t == "int" || t == "uint" || t == "Number" || t == "Boolean" || t == "*" || t == "Object" || t == "Array" || t == "Class" || t == "Function";
      }

      public function th_start(domain:ApplicationDomain) : void
      {
         var names:* = undefined;
         var n:String = null;
         var c:* = undefined;
         var v:XML = null;
         if(this.th_slots != null)
         {
            return;
         }
         this.th_slots = [];
         try
         {
            names = domain.getQualifiedDefinitionNames();
         }
         catch(err:Error)
         {
            this.cs_log("theme: cannot list the game classes: " + err.message);
            return;
         }
         for each(n in names)
         {
            try
            {
               c = domain.getDefinition(n);
               if(!(c is Class))
               {
                  continue;
               }
               var cx:XML = describeType(c);
               this.gf_note_class(c,cx);
               for each(v in cx.elements("variable"))
               {
                  if(!th_skip_type(String(v.attribute("type"))))
                  {
                     this.th_slots.push([c,String(v.attribute("name"))]);
                  }
               }
            }
            catch(err2:Error)
            {
            }
         }
         this.cs_log("theme: " + this.th_slots.length + " static fields to watch");
         this.stage.addEventListener(Event.ENTER_FRAME,this.th_tick);
      }

      private function th_tick(e:Event) : void
      {
         var s:Array = null;
         var val:* = undefined;
         var looked:int = 0;
         this.th_frames++;
         for each(s in this.th_slots)
         {
            try
            {
               val = s[0][s[1]];
            }
            catch(err:Error)
            {
               continue;
            }
            if(val == null || typeof val != "object" || this.th_seen[val])
            {
               continue;
            }
            this.th_seen[val] = true;
            this.th_examine(val,1);
            if(++looked >= 150)
            {
               break;
            }
         }
         if(this.th_frames >= TH_MAX_FRAMES)
         {
            this.stage.removeEventListener(Event.ENTER_FRAME,this.th_tick);
            this.cs_log("theme: done looking, " + this.th_found + " palette(s) recoloured");
         }
      }

      private function th_examine(obj:Object, depth:int) : void
      {
         var x:XML = null;
         var v:XML = null;
         var child:* = undefined;
         try
         {
            x = describeType(obj);
         }
         catch(err:Error)
         {
            return;
         }
         if(this.th_is_palette(obj,x))
         {
            this.th_recolour(obj,x);
            return;
         }
         if(depth <= 0)
         {
            return;
         }
         for each(v in x.elements("variable"))
         {
            if(th_skip_type(String(v.attribute("type"))))
            {
               continue;
            }
            try
            {
               child = obj[String(v.attribute("name"))];
            }
            catch(err2:Error)
            {
               continue;
            }
            if(child != null && typeof child == "object" && !this.th_seen[child])
            {
               this.th_seen[child] = true;
               this.th_examine(child,depth - 1);
            }
         }
      }

      private static function th_is_teal(c:int) : Boolean
      {
         var r:int = c >> 16 & 0xFF;
         var g:int = c >> 8 & 0xFF;
         var b:int = c & 0xFF;
         return c >= 0 && c <= 0xFFFFFF && Math.max(r,g,b) <= 0x90 && g >= r + 8 && b >= r;
      }

      private function th_is_palette(obj:Object, x:XML) : Boolean
      {
         var v:XML = null;
         var ints:int = 0;
         var teal:int = 0;
         for each(v in x.elements("variable"))
         {
            if(String(v.attribute("type")) == "int")
            {
               ints++;
               try
               {
                  if(th_is_teal(int(obj[String(v.attribute("name"))])))
                  {
                     teal++;
                  }
               }
               catch(err:Error)
               {
               }
            }
         }
         return ints >= 15 && teal >= 5;
      }

      // Dark teal colours become greys of the same order: the darkest UI
      // colour lands near #121212, light panels near #292929. The palette
      // also holds plain numbers (font sizes, margins: 0, 12, 20...); those
      // are never touched, only values above 0xFF with a teal tint.
      private static function th_dark(c:int) : int
      {
         var r:int = c >> 16 & 0xFF;
         var g:int = c >> 8 & 0xFF;
         var b:int = c & 0xFF;
         if(c <= 0xFF || !th_is_teal(c))
         {
            return c;
         }
         // The Café message cards: a little darker than the other panels.
         if(c == 0x223B4D)
         {
            return 0x171A1F;
         }
         // Cool blue-grey like the mockup: background ~#101419, cards ~#1D2126.
         var grey:int = int(0x0A + (0.3 * r + 0.59 * g + 0.11 * b) * 0.42 + 0.5);
         var nr:int = Math.max(0,grey - 3);
         var ng:int = Math.min(255,grey + 1);
         var nb:int = Math.min(255,grey + 6);
         return nr << 16 | ng << 8 | nb;
      }

      private function th_recolour(obj:Object, x:XML) : void
      {
         var v:XML = null;
         var name:String = null;
         var old:int = 0;
         var changed:Array = [];
         for each(v in x.elements("variable"))
         {
            if(String(v.attribute("type")) != "int")
            {
               continue;
            }
            name = String(v.attribute("name"));
            try
            {
               old = int(obj[name]);
               if(th_dark(old) != old)
               {
                  obj[name] = th_dark(old);
                  changed.push(old.toString(16) + ">" + th_dark(old).toString(16));
               }
            }
            catch(err:Error)
            {
            }
         }
         this.th_found++;
         this.cs_log("theme: palette recoloured, " + changed.length + " colours: " + changed.join(" "));
      }
