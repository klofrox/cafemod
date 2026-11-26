
      // ---- GIF avatars, seen only here ----
      //
      // The game keeps every downloaded image in one cache (address ->
      // BitmapData) and every avatar of a player shares that BitmapData. The
      // proxy sends "GIF <avatar id> <delays> <png frames>"; each frame we
      // draw the GIF's current frame into the player's cached avatar image,
      // so it moves in the Café, the topic list and the profile alike. Not
      // loaded yet? Our own image goes into the cache under that address.

      private static const GF_URL:String = "http://avatars.atelier801.com/";

      private var gf_gifs:Object = {};

      private var gf_cache_classes:Array = [];

      private var gf_cache:Object = null;

      private var gf_frames_seen:int = 0;

      // Called from th_start for every game class: the image loader class has
      // a static list of Loaders next to its cache.
      private function gf_note_class(c:*, x:XML) : void
      {
         var v:XML = null;
         for each(v in x.elements("variable"))
         {
            if(String(v.attribute("type")).indexOf("Vector.<flash.display::Loader>") != -1)
            {
               this.gf_cache_classes.push(c);
               return;
            }
         }
      }

      private function gf_find_cache() : Object
      {
         var c:* = undefined;
         var v:XML = null;
         var t:String = null;
         var val:* = undefined;
         var k:String = null;
         for each(c in this.gf_cache_classes)
         {
            for each(v in describeType(c).elements("variable"))
            {
               t = String(v.attribute("type"));
               if(t != "Object" && t != "flash.utils::Dictionary" && t != "*")
               {
                  continue;
               }
               try
               {
                  val = c[String(v.attribute("name"))];
               }
               catch(err:Error)
               {
                  continue;
               }
               if(val == null)
               {
                  continue;
               }
               for(k in val)
               {
                  if(k.indexOf("http") == 0 && val[k] is BitmapData)
                  {
                     this.cs_log("gif: found the game's image cache");
                     return val;
                  }
                  break;
               }
            }
         }
         return null;
      }

      private static function gf_base64(s:String) : ByteArray
      {
         var table:String = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
         var out:ByteArray = new ByteArray();
         var buf:int = 0;
         var bits:int = 0;
         var i:int = 0;
         var v:int = 0;
         for(i = 0; i < s.length; i++)
         {
            v = table.indexOf(s.charAt(i));
            if(v < 0)
            {
               continue;
            }
            buf = buf << 6 | v;
            bits += 6;
            if(bits >= 8)
            {
               bits -= 8;
               out.writeByte(buf >> bits & 0xFF);
            }
         }
         out.position = 0;
         return out;
      }

      // "GIF <id> <delay,delay,...> <png,png,...>"
      public function gf_add(line:String) : void
      {
         var parts:Array = line.split(" ");
         if(parts.length < 4)
         {
            return;
         }
         var id:int = int(parts[1]);
         var delays:Array = String(parts[2]).split(",");
         var pngs:Array = String(parts[3]).split(",");
         var gif:Object = {"id":id,"frames":new Array(pngs.length),"delays":[],"total":0,"ready":0,"shown":-1,"targets":[]};
         var i:int = 0;
         for(i = 0; i < delays.length; i++)
         {
            gif.delays.push(Math.max(20,int(delays[i])));
            gif.total += gif.delays[i];
         }
         for(i = 0; i < pngs.length; i++)
         {
            this.gf_load_frame(gif,i,gf_base64(pngs[i]));
         }
         this.gf_gifs[id] = gif;
         this.cs_log("gif: avatar " + id + ", " + pngs.length + " frames");
         if(!this.gf_ticking)
         {
            this.gf_ticking = true;
            this.stage.addEventListener(Event.ENTER_FRAME,this.gf_tick);
         }
      }

      private var gf_ticking:Boolean = false;

      private function gf_load_frame(gif:Object, i:int, bytes:ByteArray) : void
      {
         var l:Loader = new Loader();
         l.contentLoaderInfo.addEventListener(Event.COMPLETE,function(e:Event):void
         {
            gif.frames[i] = Bitmap(l.content).bitmapData;
            gif.ready++;
         });
         l.loadBytes(bytes);
      }

      private function gf_tick(e:Event) : void
      {
         var key:String = null;
         var gif:Object = null;
         var url:String = null;
         var bmd:BitmapData = null;
         var t:int = 0;
         var n:int = 0;
         var acc:int = 0;
         var frame:BitmapData = null;
         var target:BitmapData = null;
         if(this.gf_cache == null)
         {
            if(this.gf_frames_seen++ % 24 == 0)
            {
               this.gf_cache = this.gf_find_cache();
            }
            if(this.gf_cache == null)
            {
               return;
            }
         }
         for(key in this.gf_gifs)
         {
            gif = this.gf_gifs[key];
            if(gif.ready < gif.frames.length || gif.total <= 0)
            {
               continue;
            }
            url = GF_URL + int(gif.id) % 10000 + "/" + gif.id + "_50.jpg";
            bmd = this.gf_cache[url] as BitmapData;
            if(bmd == null)
            {
                // Not downloaded yet: the game will use ours.
               bmd = new BitmapData(50,50,false,0x101419);
               this.gf_cache[url] = bmd;
            }
            if((gif.targets as Array).indexOf(bmd) == -1)
            {
               // Keep every image the game handed out for this address
               // (ours and, once downloaded, the real one).
               gif.targets.push(bmd);
               gif.shown = -1;
            }
            t = getTimer() % int(gif.total);
            n = 0;
            acc = int(gif.delays[0]);
            while(acc <= t && n < gif.frames.length - 1)
            {
               n++;
               acc += int(gif.delays[n]);
            }
            if(n == gif.shown)
            {
               continue;
            }
            gif.shown = n;
            frame = gif.frames[n];
            for each(target in gif.targets)
            {
               try
               {
                  target.lock();
                  target.draw(frame,new Matrix(target.width / frame.width,0,0,target.height / frame.height),null,null,null,true);
                  target.unlock();
               }
               catch(err:Error)
               {
               }
            }
         }
      }
