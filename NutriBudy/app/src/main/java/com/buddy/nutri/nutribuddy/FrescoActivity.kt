package com.buddy.nutri.nutribuddy

    import android.net.Uri
    import com.facebook.drawee.backends.pipeline.Fresco
    import android.os.Bundle
    import android.support.v7.app.AppCompatActivity
    import android.view.View
    import com.facebook.drawee.view.SimpleDraweeView



    class FrescoActivity : AppCompatActivity() {

        override fun onCreate(savedInstanceState: Bundle?) {
            super.onCreate(savedInstanceState)

            val imageUri = Uri.parse("http://172.30.177.39:5001/image/Meeseeks.png")
            val draweeView = findViewById<View>(R.id.sdvImage) as SimpleDraweeView
            draweeView.setImageURI(imageUri)
        }

    }
