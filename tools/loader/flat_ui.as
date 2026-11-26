
      // ---- Flat UI: replace the wood with flat dark panels ----
      //
      // Found with the parts tree of the running game:
      //   $FenetreBaseFn  the wood frame, title strip and leaves of a window
      //   $FondBouton     the teal background of a wide button
      //   $Interface      the bottom bar: child 0 holds the wood, the list
      //                   panels are containers of two shapes at 0,0
      // Windows get a frame of our own; the other pieces keep their exact
      // outline but are filled with one flat colour (a ColorTransform that
      // drops their colours and keeps their alpha), plus a thin inner edge.

      private static const FU_BG:uint = 0x0F1317;

      private static const FU_TITLE:uint = 0x151A20;

      private static const FU_EDGE:uint = 0x2A3039;

      private static const FU_BUTTON:uint = 0x262B33;

      private static const FU_PANEL:uint = 0x14181D;

      private var fu_done:Dictionary = new Dictionary(true);

      // Window -> the rectangle of the frame we drew (the Café panel uses it).
      private var fu_rects:Dictionary = new Dictionary(true);

      private static function fu_name(d:Object) : String
      {
         return getQualifiedClassName(d);
      }

      private static function fu_flat(d:DisplayObject, colour:uint, edge:Boolean) : void
      {
         d.transform.colorTransform = new ColorTransform(0,0,0,1,colour >> 16 & 0xFF,colour >> 8 & 0xFF,colour & 0xFF,0);
         d.filters = edge ? [new GlowFilter(FU_EDGE,1,2,2,3,1,true)] : [];
      }

      // Look through what was just added for the wood pieces.
      private function fu_scan(d:DisplayObject, depth:int) : void
      {
         var c:DisplayObjectContainer = d as DisplayObjectContainer;
         var i:int = 0;
         var name:String = fu_name(d);
         if(this.fu_done[d])
         {
            return;
         }
         if(name == "$FenetreBaseFn")
         {
            this.fu_done[d] = true;
            this.fu_window_frame(d);
            return;
         }
         if(name == "$Refresh")
         {
            this.cp_restyle(d,"refresh");
            this.cp_setup_cafe(d);
            return;
         }
         if(name == "$I_Croix1" || name == "$I_Croix2")
         {
            this.cp_restyle(d,"close");
            return;
         }
         if(name == "$FondBouton")
         {
            this.fu_done[d] = true;
            fu_flat(d,FU_BUTTON,true);
            return;
         }
         if(name == "$Interface" && c != null)
         {
            // Not marked done: its panels may be added after it; flattening
            // again gives the same result.
            this.fu_interface(c);
            return;
         }
         if(c == null || depth <= 0)
         {
            return;
         }
         for(i = 0; i < c.numChildren; i++)
         {
            this.fu_scan(c.getChildAt(i),depth - 1);
         }
      }

      public function fu_rescan(d:DisplayObject) : void
      {
         try
         {
            this.fu_scan(d,4);
         }
         catch(err:Error)
         {
            this.cs_log("flat ui failed: " + err.message);
         }
      }

      private function fu_window_frame(fen:DisplayObject) : void
      {
         var win:DisplayObjectContainer = fen.parent;
         if(win == null)
         {
            return;
         }
         // The wood overhangs the window by ~11 px (leaves); stay just inside it.
         var b:Rectangle = fen.getBounds(win);
         var x:Number = b.x + 4;
         var y:Number = b.y;
         var w:Number = b.width - 8;
         var h:Number = b.height - 4;
         var frame:Sprite = new Sprite();
         frame.graphics.lineStyle(1,FU_EDGE,1,true);
         frame.graphics.beginFill(FU_BG);
         frame.graphics.drawRoundRect(x,y,w,h,14,14);
         frame.graphics.endFill();
         // Title strip: the top 30 px, a shade lighter, with a line under it.
         frame.graphics.lineStyle();
         frame.graphics.beginFill(FU_TITLE);
         frame.graphics.drawRoundRectComplex(x + 1,y + 1,w - 2,29,6,6,0,0);
         frame.graphics.endFill();
         frame.graphics.lineStyle(1,FU_EDGE,1,true);
         frame.graphics.moveTo(x + 1,y + 30);
         frame.graphics.lineTo(x + w - 1,y + 30);
         frame.filters = [new DropShadowFilter(4,90,0,0.5,12,12,1,2)];
         frame.mouseEnabled = false;
         win.addChildAt(frame,win.getChildIndex(fen));
         this.fu_rects[win] = new Rectangle(x,y,w,h);
         fen.visible = false;
         this.cs_log("flat ui: window frame " + int(w) + "x" + int(h));
      }

      private function fu_interface(itf:DisplayObjectContainer) : void
      {
         var i:int = 0;
         var j:int = 0;
         var d:DisplayObject = null;
         var c:DisplayObjectContainer = null;
         var flat:int = 0;
         if(itf.numChildren > 0)
         {
            // Child 0: the wood of the whole bottom bar.
            fu_flat(itf.getChildAt(0),FU_BG,true);
            flat++;
         }
         // List panels (players, room): containers whose first children are
         // shapes at 0,0 - their parchment / wood backgrounds.
         for(i = 1; i < itf.numChildren; i++)
         {
            c = itf.getChildAt(i) as DisplayObjectContainer;
            if(c == null)
            {
               continue;
            }
            for(j = 0; j < c.numChildren; j++)
            {
               d = c.getChildAt(j);
               if(d is Shape && d.x == 0 && d.y == 0 && d.width >= 100 && d.height >= 60)
               {
                  fu_flat(d,FU_PANEL,j == 0);
                  flat++;
               }
            }
         }
         this.cs_log("flat ui: bottom bar, " + flat + " pieces flattened");
      }
