package com.maxplayer.app;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.*;
import android.widget.FrameLayout;

public class MainActivity extends Activity {
    private WebView web;
    private ValueCallback<Uri[]> chooser;
    private View customView;
    private WebChromeClient.CustomViewCallback customCb;
    private FrameLayout root;
    private static final int REQ = 7;

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setBackgroundDrawableResource(android.R.color.black);
        root = new FrameLayout(this);
        web = new WebView(this);
        web.setBackgroundColor(0xFF000000);
        root.addView(web, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView w, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (chooser != null) chooser.onReceiveValue(null);
                chooser = cb;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                try { startActivityForResult(Intent.createChooser(i, "영상 선택"), REQ); }
                catch (Exception e) { chooser = null; return false; }
                return true;
            }
            @Override public void onShowCustomView(View v, CustomViewCallback cb) {
                if (customView != null) { cb.onCustomViewHidden(); return; }
                customView = v; customCb = cb;
                root.addView(v, new FrameLayout.LayoutParams(-1, -1));
                web.setVisibility(View.GONE);
                immersive();
            }
            @Override public void onHideCustomView() {
                if (customView == null) return;
                root.removeView(customView); customView = null;
                web.setVisibility(View.VISIBLE);
                if (customCb != null) customCb.onCustomViewHidden();
            }
        });
        web.loadUrl("file:///android_asset/index.html");
        handleIntent(getIntent());
    }

    private void handleIntent(Intent i) {
        // Videos opened from other apps: no JS bridge for file handles, so just show the app.
    }
    @Override protected void onNewIntent(Intent i) { super.onNewIntent(i); handleIntent(i); }

    @Override protected void onActivityResult(int req, int res, Intent d) {
        if (req != REQ || chooser == null) { super.onActivityResult(req, res, d); return; }
        Uri[] r = null;
        if (res == RESULT_OK && d != null) {
            if (d.getClipData() != null) {
                int n = d.getClipData().getItemCount();
                r = new Uri[n];
                for (int k = 0; k < n; k++) r[k] = d.getClipData().getItemAt(k).getUri();
            } else if (d.getData() != null) r = new Uri[]{d.getData()};
        }
        chooser.onReceiveValue(r); chooser = null;
    }

    private void immersive() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }
    @Override public void onWindowFocusChanged(boolean f) { super.onWindowFocusChanged(f); if (f) immersive(); }

    @Override public void onBackPressed() {
        if (customView != null) { web.evaluateJavascript("document.exitFullscreen&&document.exitFullscreen()", null); return; }
        // Let the page decide (player -> home); exit when already on the home screen.
        web.evaluateJavascript("(function(){var p=document.getElementById('player');if(p&&!p.hidden){document.getElementById('bBack').click();return 1}return 0})()",
            new ValueCallback<String>() { public void onReceiveValue(String v) { if (!"1".equals(v)) finish(); } });
    }
    @Override protected void onPause() { super.onPause(); }
    @Override protected void onDestroy() { if (web != null) web.destroy(); super.onDestroy(); }
}
