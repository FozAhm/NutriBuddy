package com.buddy.nutri.nutribuddy

import android.content.Intent
import android.support.v7.app.AppCompatActivity
import android.os.Bundle
import android.widget.ImageButton

class MainActivity : AppCompatActivity()
{
    private var splashImage: ImageButton? = null
    override fun onCreate(savedInstanceState: Bundle?)
    {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        setupUI()

    }

    private fun setupUI()
    {
        splashImage = findViewById<ImageButton>(R.id.splashButton) as ImageButton

        splashImage!!.setOnClickListener {

            //val intent = Intent(this, CameraActivity::class.java)
            val intent = Intent(this, FrescoActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            startActivity(intent)

        }
    }
}
