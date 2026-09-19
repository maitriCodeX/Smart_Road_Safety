package com.example.smartroadsafety

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.widget.AppCompatButton
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.smartroadsafety.data.DataRepository
import com.example.smartroadsafety.model.UserProfile
import kotlinx.coroutines.launch

class ProfileFragment : Fragment() {

    private lateinit var layoutAvatarContainer: FrameLayout
    private lateinit var ivProfileAvatar: ImageView
    private lateinit var etProfileEmail: EditText
    private lateinit var etProfilePassword: EditText
    private lateinit var etProfilePhone: EditText
    private lateinit var etProfileRelativePhone: EditText
    private lateinit var etProfileAge: EditText
    private lateinit var etProfileBloodGroup: EditText
    private lateinit var etProfileCarPlate: EditText
    private lateinit var btnSaveProfile: AppCompatButton

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_profile, container, false)
        initViews(view)
        loadProfileData()
        setupListeners()
        return view
    }

    private fun initViews(view: View) {
        layoutAvatarContainer = view.findViewById(R.id.layoutAvatarContainer)
        ivProfileAvatar = view.findViewById(R.id.ivProfileAvatar)
        etProfileEmail = view.findViewById(R.id.etProfileEmail)
        etProfilePassword = view.findViewById(R.id.etProfilePassword)
        etProfilePhone = view.findViewById(R.id.etProfilePhone)
        etProfileRelativePhone = view.findViewById(R.id.etProfileRelativePhone)
        etProfileAge = view.findViewById(R.id.etProfileAge)
        etProfileBloodGroup = view.findViewById(R.id.etProfileBloodGroup)
        etProfileCarPlate = view.findViewById(R.id.etProfileCarPlate)
        btnSaveProfile = view.findViewById(R.id.btnSaveProfile)
    }

    private fun loadProfileData() {
        val cachedProfile = DataRepository.getUserProfile()
        renderProfile(cachedProfile)

        viewLifecycleOwner.lifecycleScope.launch {
            val liveProfile = DataRepository.fetchUserProfileOnline()
            renderProfile(liveProfile)
        }
    }

    private fun renderProfile(profile: UserProfile) {
        if (!isAdded || context == null) return
        etProfileEmail.setText(profile.email)
        etProfilePassword.setText(profile.password)
        etProfilePhone.setText(profile.phoneNumber)
        val emergencyPhone = SafetyEngine.getEmergencyTargetPhone()
        val displayPhone = if (emergencyPhone.isNotBlank()) emergencyPhone else profile.relativePhoneNumber
        etProfileRelativePhone.setText(displayPhone)
        etProfileAge.setText(profile.age.toString())
        etProfileBloodGroup.setText(profile.bloodGroup)
        etProfileCarPlate.setText(profile.carPlateNumber)
    }

    private fun setupListeners() {
        layoutAvatarContainer.setOnClickListener {
            Toast.makeText(requireContext(), "Profile photo updated", Toast.LENGTH_SHORT).show()
        }

        btnSaveProfile.setOnClickListener {
            handleSaveProfile()
        }
    }

    private fun handleSaveProfile() {
        val email = etProfileEmail.text.toString().trim()
        val password = etProfilePassword.text.toString().trim()
        val phone = etProfilePhone.text.toString().trim()
        val relativePhone = etProfileRelativePhone.text.toString().trim()
        val ageStr = etProfileAge.text.toString().trim()
        val bloodGroup = etProfileBloodGroup.text.toString().trim().uppercase()
        val carPlate = etProfileCarPlate.text.toString().trim().uppercase()

        if (email.isEmpty()) {
            etProfileEmail.error = "Email cannot be empty"
            return
        }

        if (password.isEmpty()) {
            etProfilePassword.error = "Password cannot be empty"
            return
        }

        val age = ageStr.toIntOrNull() ?: 24

        val updated = UserProfile(
            userId = DataRepository.getUserProfile().userId,
            name = DataRepository.getUserProfile().name,
            profilePictureUrl = "",
            email = email,
            password = password,
            phoneNumber = phone,
            relativePhoneNumber = relativePhone,
            age = age,
            bloodGroup = bloodGroup,
            carPlateNumber = carPlate
        )

        btnSaveProfile.isEnabled = false
        btnSaveProfile.text = "Saving Profile..."

        viewLifecycleOwner.lifecycleScope.launch {
            val (success, message) = DataRepository.updateUserProfileOnline(updated)
            btnSaveProfile.isEnabled = true
            btnSaveProfile.text = "Save Profile"
            if (relativePhone.isNotEmpty()) {
                SafetyEngine.setEmergencyTargetPhone(relativePhone)
            }
            Toast.makeText(requireContext(), message, Toast.LENGTH_SHORT).show()
        }
    }
}
