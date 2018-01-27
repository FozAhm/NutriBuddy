package com.buddy.nutri.nutribudy

import android.support.v7.app.AppCompatActivity
import android.os.Bundle
import android.widget.Button
import android.widget.ImageButton
import android.view.View

class MainActivity : AppCompatActivity()
{
    private var splashImage: ImageButton? = null
    override fun onCreate(savedInstanceState: Bundle?)
    {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        setuoUI()

    }

    fun setuoUI()
    {
        splashImage = findViewById<ImageButton>(R.id.splashButton) as ImageButton
    }
}
